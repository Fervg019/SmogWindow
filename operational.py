"""Issue ONE next-day forecast from a daily PM2.5 history, exactly as the frozen protocol would.

This is the operational workflow behind the replay: give it a CSV with the dataset's columns (date, pm2_5,
pm10, ...) that ends on the day you are standing on, and it fits the frozen model on everything dated on or
before that day, calibrates the uncertainty from earlier out-of-sample errors, and returns a planning summary.
It never invents or fills missing data: a gap in the 14-day window means no forecast is issued.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from evaluation import SPECS, build_frame, walk_forward, calibrate, load_series, SCHEME_LABEL
from model import features, fit_model, predict, columns_for, data_quality

ROOT = Path(__file__).resolve().parent
CAVEATS = ['Values are CAMS atmospheric-model estimates, not measurements at a school or a monitor.',
           'A planning flag means "prepare an alternative"; no flag does NOT mean outdoor activity is safe.',
           'Check official air-quality guidance and current local readings before deciding.',
           'Research prototype: not medical advice, not a safety clearance, not validated by any school.']


def frozen_selection():
    return json.loads((ROOT / 'results/selection_frozen.json').read_text())


def issue_forecast(raw, asof=None, threshold=55., ratio=3, first_target='2023-03-01'):
    frozen = frozen_selection(); model_name = frozen['forecast_model']; scheme = frozen['uncertainty_scheme']
    raw = raw.copy().sort_index()
    asof = pd.Timestamp(asof) if asof is not None else raw.pm2_5.last_valid_index()
    raw = raw.loc[:asof]                       # nothing after the origin date can be used
    dq = data_quality(raw, asof)
    result = {'origin': str(asof.date()), 'target': str((asof + pd.Timedelta(days=1)).date()), 'data_quality': dq, 'caveats': CAVEATS,
              'model': model_name, 'uncertainty_method': SCHEME_LABEL[scheme], 'threshold': threshold, 'ratio': ratio}
    need = [c for c in columns_for(SPECS[model_name], list(features(raw)[0].columns), features(raw)[2])]
    x_all, _, history = features(raw)
    if not dq['complete'] or asof not in x_all.index or x_all.loc[asof, need].isna().any():
        result.update(issued=False, reason='; '.join(dq['flags']) or 'Not enough complete history for the model inputs.')
        return result
    x, y, history, tdates = build_frame(raw)
    cfg = SPECS[model_name]; cols = columns_for(cfg, list(x.columns), history)
    last_train = tdates[tdates <= asof].max()
    specs = {model_name: cfg, 'Persistence': SPECS['Persistence']}
    wf = walk_forward(x, y, tdates, history, pd.Timestamp(first_target), last_train, specs=specs)
    fitted = fit_model(x.loc[tdates <= asof, cols], y[tdates <= asof], cfg)
    xi = x_all.loc[[asof]]
    p_model = float(predict(fitted, xi)[0]); p_pers = float(xi.pm_lag_0.iloc[0])
    target = asof + pd.Timedelta(days=1)
    dates = list(wf.index) + [target]
    out = {}
    for name, p in ((model_name, p_model), ('Persistence', p_pers)):
        c = calibrate(dates, list(wf[name].values) + [p], list(wf.actual.values) + [np.nan], scheme).iloc[-1]
        out[name] = {k: float(c[k]) for k in ('lo', 'hi', 's1', 's3', 's5')}
    score = {n: out[n][f's{ratio}'] for n in out}
    result.update(issued=True, forecast=p_model, interval_80=[out[model_name]['lo'], out[model_name]['hi']], persistence=p_pers,
                  warning_score=score[model_name], persistence_warning_score=score['Persistence'],
                  planning_flag=bool(score[model_name] > threshold), persistence_flag=bool(score['Persistence'] > threshold),
                  calibration_history_days=int((wf.index < target).sum()))
    ab = float(abs(x_all.loc[asof, 'pm_change'])); result['abrupt_change_today'] = bool(ab > frozen['abrupt_cutoff'])
    return result


def summary_text(r):
    if not r['issued']:
        return f"SmogWindow planning summary - NO FORECAST ISSUED for {r['target']}\nReason: {r['reason']}\n" + '\n'.join('- ' + c for c in r['caveats'])
    lo, hi = r['interval_80']
    L = [f"SmogWindow planning summary - Lahore, PM2.5 (modeled)", f"Forecast origin: {r['origin']}   Forecast for: {r['target']}",
         f"Forecast daily mean: {r['forecast']:.0f} ug/m3   80% range: {lo:.0f}-{hi:.0f} ug/m3   (method: {r['uncertainty_method']})",
         f"Persistence ('tomorrow = today'): {r['persistence']:.0f} ug/m3",
         f"Assumptions: planning threshold {r['threshold']:.0f} ug/m3; a missed high day is treated as {r['ratio']}x as costly as a false alarm (illustrative, not a regulation).",
         f"Planning flag (model + margin): {'YES - prepare an indoor / alternative plan' if r['planning_flag'] else 'NO flag at these settings (this is not a safety clearance)'}",
         f"Calibrated-persistence flag: {'YES' if r['persistence_flag'] else 'NO'}" + ('   <-- the two methods disagree' if r['planning_flag'] != r['persistence_flag'] else ''),
         'Data checks: ' + ('14-day window complete.' if r['data_quality']['complete'] else '; '.join(r['data_quality']['flags']))]
    extra = [f for f in r['data_quality']['flags'] if f]
    if r['data_quality']['complete'] and extra: L.append('Warnings: ' + ' '.join(extra))
    if r.get('abrupt_change_today'): L.append('Caution: pollution changed abruptly today; next-day forecasts were less accurate after abrupt changes in most test periods.')
    L += ['Limits:'] + ['- ' + c for c in r['caveats']]
    return '\n'.join(L)
