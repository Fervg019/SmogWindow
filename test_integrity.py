"""Integrity tests: python test_integrity.py   (needs run_all.py and build_dashboard.py to have been run; ~1-2 minutes)."""
from pathlib import Path
import json, re, tempfile
import numpy as np
import pandas as pd
import evaluation as ev
from model import features, warning_metrics, data_quality
R = Path(__file__).resolve().parent
raw = ev.load_series(R / 'data/air_quality_historical.csv')
T = pd.Timestamp

# 1. Features never see the future -------------------------------------------------------------
x, y, h = features(raw)
cut = T('2025-06-30')
mut = raw.copy(); mut.loc[mut.index > cut, :] = 999999
x2, _, _ = features(mut)
pd.testing.assert_frame_equal(x.loc[:cut], x2.loc[:cut])
prefix, _, _ = features(raw.loc[:cut]); pd.testing.assert_frame_equal(x.loc[:cut], prefix)
print('PASS features: future-mutation and prefix invariance')

# 2. Walk-forward forecasts are unaffected by anything dated after the forecast month -----------
xa, ya, ha, ta = ev.build_frame(raw); xb, yb, hb, tb = ev.build_frame(mut)
a = ev.walk_forward(xa, ya, ta, ha, T('2025-01-01'), cut)
b = ev.walk_forward(xb, yb, tb, hb, T('2025-01-01'), cut)
pd.testing.assert_frame_equal(a.drop(columns='actual'), b.drop(columns='actual'), atol=1e-9)
print('PASS walk-forward: mutating all data after 2025-06-30 changes no forecast made before it (all 11 candidates)')

# 3. Calibration for day i uses only errors of days before i --------------------------------------
wf = pd.read_csv(R / 'results/walkforward_predictions.csv', parse_dates=['target_date'])
dates, pred, act = wf.target_date.values, wf['Persistence'].values, wf.actual.values
i = 420
for s in ev.SCHEMES:
    base = ev.calibrate(dates, pred, act, s)
    act2 = act.copy(); act2[i:] = 1e6; alt = ev.calibrate(dates, pred, act2, s)
    pd.testing.assert_frame_equal(base.iloc[:i + 1], alt.iloc[:i + 1])
print('PASS calibration: changing actuals from day i onward leaves intervals/margins up to day i unchanged (6 schemes)')

# 4. Model/uncertainty choice depends on development data only -------------------------------------
import run_all
tmp = tempfile.mkdtemp(); real_out = run_all.OUT; run_all.OUT = Path(tmp)
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()): run_all.main('dev')
run_all.OUT = real_out
f_dev = json.loads((Path(tmp) / 'selection_frozen.json').read_text()); f_full = json.loads((R / 'results/selection_frozen.json').read_text())
assert f_dev == f_full, 'selection changes when 2025/2026 data are added: it was not chosen on development data alone'
print('PASS selection: identical when 2025-2026 are removed from the data entirely (hash', f_full['sha256'][:12] + ')')

# 5. Windows and alignment --------------------------------------------------------------------------
audit = json.loads((R / 'results/audit.json').read_text()); w = audit['windows']
assert w['development'][1] < w['benchmark_2025'][0] and w['benchmark_2025'][1] < w['holdout_2026'][0]
assert w['benchmark_2025'][2] == 365 and w['holdout_2026'][2] == 49
assert (pd.to_datetime(wf.target_date) - pd.to_datetime(pd.read_csv(R / 'results/walkforward_predictions.csv').origin_date) == pd.Timedelta(days=1)).all()
assert np.allclose(pd.read_csv(R / 'results/walkforward_predictions.csv').set_index('origin_date')['Persistence'], x.pm_lag_0.reindex(pd.read_csv(R / 'results/walkforward_predictions.csv').origin_date).values)
p = pd.read_csv(R / 'results/walkforward_predictions.csv'); q = p.dropna(subset=['model_lo', 'model_hi', 'persistence_lo', 'persistence_hi']); assert len(q) > 800 and q.model_lo.le(q.model_hi).all() and q.model_lo.ge(0).all() and q.persistence_lo.le(q.persistence_hi).all()
print('PASS windows: development < 2025 < 2026; 365 + 49 evaluation days; one-day alignment; ordered intervals')

# 6. Warning counts ----------------------------------------------------------------------------------
assert warning_metrics([60, 20], [60, 60])['fp'] == 1 and warning_metrics([60, 20], [20, 20])['fn'] == 1
assert ev.day_costs([60, 20, 60, 20], [60, 60, 20, 20], 55, 3).tolist() == [0, 1, 3, 0]
assert ev.block_bootstrap(np.arange(50.)) == ev.block_bootstrap(np.arange(50.))
print('PASS warning/cost arithmetic and deterministic bootstrap')

# 7. Dashboard embeds exactly the exported results ---------------------------------------------------
html = (R / 'SmogWindow_dashboard.html').read_text(encoding='utf-8')
D = json.loads(re.search(r'const D=(\{.*?\});\nconst \$', html, re.S).group(1))
ev_rows = p[p.target_date >= '2025-01-01'].reset_index(drop=True)
assert len(D['rows']) == len(ev_rows) == 414
model_col = D['model']
for k in (0, 200, 413):
    r, e = D['rows'][k], ev_rows.iloc[k]
    assert r['o'] == e.origin_date and abs(r['m'] - e[model_col]) < 6e-3 and abs(r['ms'][1] - e.model_s3) < 6e-3 and abs(r['ps'][1] - e.persistence_s3) < 6e-3 and abs(r['a'] - e.actual) < 6e-3
print('PASS dashboard data parity with results/walkforward_predictions.csv')

# 8. Operational forecast: no future data, refuses on gaps ------------------------------------------------
from operational import issue_forecast
r1 = issue_forecast(raw, '2025-05-21'); r2 = issue_forecast(mut, '2025-05-21')
assert r1['issued'] and abs(r1['forecast'] - r2['forecast']) < 1e-9 and r1['interval_80'] == r2['interval_80']
gap = raw.copy(); gap.loc[T('2025-05-15'), 'pm2_5'] = np.nan
r3 = issue_forecast(gap, '2025-05-21'); assert r3['issued'] is False and '1 of the last 14' in r3['reason']
assert not data_quality(raw, '2025-05-21')['missing_days']
print('PASS operational forecast: ignores later data; no forecast when the 14-day window has a gap')

# 9. Ground-validation tool, SYNTHETIC test data (never reported anywhere) -----------------------------------
import validate_ground as vg
cams = raw.pm2_5
rng = np.random.default_rng(1)
days = pd.date_range('2025-01-01', '2025-12-31')
hours = pd.DataFrame({'Date (LT)': np.repeat(days, 24) + pd.to_timedelta(np.tile(np.arange(24), len(days)), unit='h')})
hours['Raw Conc.'] = np.repeat(cams.reindex(days).values * .8, 24) + rng.normal(0, 5, len(hours))
hours.loc[::50, 'Raw Conc.'] = -999
g = vg.daily_ground(hours, hourly=True)
res = vg.validate(g, cams, p)
assert res['ok'] and res['alignment_warning'] is None and res['forecast_vs_ground']['days'] > 300 and res['cams_vs_ground']['bias_cams_minus_ground'] > 0
assert not vg.validate(g.iloc[:30], cams, p)['ok']
shifted = vg.validate(g.shift(1, freq='D'), cams, p); assert shifted['alignment_warning']
print('PASS ground validation tool on synthetic monitor data (alignment, refusal, shift warning)')

# 10. Open-Meteo parsing on a mock response -----------------------------------------------------------------------
import fetch_open_meteo as fm
t = pd.date_range('2026-02-01', periods=24 + 10, freq='h').strftime('%Y-%m-%dT%H:%M').tolist()
mock = {'hourly': {'time': t, **{v: list(np.arange(len(t), dtype=float)) for v in fm.VARS}}}
d = fm.hourly_to_daily(mock); assert len(d) == 1 and str(d.index[0].date()) == '2026-02-01'
print('PASS Open-Meteo parser drops partial days (mock response; live API untested here)')
print('ALL TESTS PASSED')
