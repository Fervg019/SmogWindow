"""Check the modeled-data results against a REAL ground monitor, once you have its data.

    python validate_ground.py --ground my_monitor.csv --time-col "Date (LT)" --value-col "Raw Conc." [--hourly] [--out results/ground_validation.json]

The CSV needs a time column and a PM2.5 column (ug/m3). With --hourly, hours are averaged per calendar day and
days with fewer than 18 valid hours are dropped. Negative values (usually missing-data codes such as -999) are dropped.
Nothing here is reported in the write-up until a real file has been supplied: no ground data are bundled."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from evaluation import load_series, mae, rmse, day_costs, PRIMARY

ROOT = Path(__file__).resolve().parent
MIN_OVERLAP_DAYS = 60
TIME_GUESS = ['Date (LT)', 'timestamp', 'datetime', 'date']
VALUE_GUESS = ['Raw Conc.', 'pm2_5', 'pm25', 'value', 'NowCast Conc.']


def daily_ground(df, time_col=None, value_col=None, hourly=False, min_hours=18):
    time_col = time_col or next(c for c in TIME_GUESS if c in df.columns)
    value_col = value_col or next(c for c in VALUE_GUESS if c in df.columns)
    t = pd.to_datetime(df[time_col], errors='coerce'); v = pd.to_numeric(df[value_col], errors='coerce')
    ok = t.notna() & v.notna() & (v >= 0)
    s = pd.Series(v[ok].values, index=t[ok].values).sort_index()
    if hourly:
        g = s.groupby(s.index.normalize()); out = g.mean()[g.count() >= min_hours]
    else:
        out = s.groupby(s.index.normalize()).mean()
    out.index.name = 'date'
    return out


def validate(ground, cams, wf, threshold=PRIMARY[0], ratio=PRIMARY[1], model_col=None):
    model_col = model_col or json.loads((ROOT / 'results/selection_frozen.json').read_text())['forecast_model']
    both = pd.concat([ground.rename('ground'), cams.rename('cams')], axis=1, join='inner').dropna()
    if len(both) < MIN_OVERLAP_DAYS:
        return {'ok': False, 'reason': f'Only {len(both)} overlapping days; at least {MIN_OVERLAP_DAYS} are needed.'}
    res = {'ok': True, 'overlap_days': int(len(both)), 'overlap_start': str(both.index.min().date()), 'overlap_end': str(both.index.max().date())}
    lagr = {}
    for k in (-1, 0, 1):
        lagr[str(k)] = float(both.ground.corr(cams.shift(-k).reindex(both.index)))    # ground(d) vs CAMS(d+k)
    res['alignment_correlation_by_day_shift'] = lagr
    res['alignment_warning'] = None if max(lagr, key=lagr.get) == '0' else 'Correlation is highest at a non-zero day shift: check timezones/day definitions before trusting any result.'
    d = both.cams - both.ground
    res['cams_vs_ground'] = {'bias_cams_minus_ground': float(d.mean()), 'mae': float(d.abs().mean()), 'rmse': float(np.sqrt((d ** 2).mean())),
                             'pearson_r': float(both.ground.corr(both.cams)), 'mean_ground': float(both.ground.mean()), 'mean_cams': float(both.cams.mean())}
    ga, ca = both.ground > threshold, both.cams > threshold
    res['exceedance_agreement_at_threshold'] = {'threshold': threshold, 'ground_high': int(ga.sum()), 'cams_high': int(ca.sum()), 'both': int((ga & ca).sum()),
                                                'ground_only': int((ga & ~ca).sum()), 'cams_only': int((~ga & ca).sum())}
    # Forecast evaluation against ground truth for the NEXT day
    w = wf.copy(); w.index = pd.to_datetime(w['target_date'])
    gnext = ground.reindex(w.index); gtoday = ground.reindex(pd.to_datetime(w['origin_date']))
    gtoday.index = w.index
    m = gnext.notna() & gtoday.notna()
    if m.sum() < MIN_OVERLAP_DAYS:
        res['forecast_vs_ground'] = {'ok': False, 'reason': f'Only {int(m.sum())} days have ground values on both origin and target dates.'}
        return res
    y = gnext[m].values; ww = w[m]; gp = gtoday[m].values
    names = {'Ground persistence (today\'s monitor reading)': gp, 'CAMS persistence': ww['Persistence'].values, 'Model forecast (trained on CAMS)': ww[model_col].values}
    fv = {'days': int(m.sum()), 'mae_vs_ground': {k: mae(y, v) for k, v in names.items()}}
    split = int(.6 * len(y)); a_, b_ = np.polyfit(ww[model_col].values[:split], y[:split], 1)
    fv['mae_model_linear_recalibrated_to_ground_first60pct_tested_last40pct'] = mae(y[split:], a_ + b_ * ww[model_col].values[split:])
    fv['mae_raw_model_last40pct'] = mae(y[split:], ww[model_col].values[split:])
    fv['recalibration_intercept_slope'] = [float(a_), float(b_)]
    pol = {'Ground persistence': gp, 'CAMS persistence + margin': ww['persistence_s3'].values, 'Model + margin': ww['model_s3'].values}
    fv['warnings_vs_ground_high_days'] = {k: {'missed': int(((y > threshold) & ~(v > threshold)).sum()), 'false_alarms': int((~(y > threshold) & (v > threshold)).sum()),
                                              'cost': float(day_costs(y, v, threshold, ratio).sum())} for k, v in pol.items()}
    fv['ground_high_days'] = int((y > threshold).sum())
    res['forecast_vs_ground'] = fv
    res['limits'] = ['One monitor is not a school site.', 'Ground values may be preliminary (not final quality-assured).',
                     'The margins (s3) were calibrated against CAMS errors, not ground errors.']
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--ground', required=True); ap.add_argument('--time-col'); ap.add_argument('--value-col')
    ap.add_argument('--hourly', action='store_true'); ap.add_argument('--out', default=str(ROOT / 'results/ground_validation.json'))
    a = ap.parse_args()
    g = daily_ground(pd.read_csv(a.ground), a.time_col, a.value_col, a.hourly)
    cams = load_series(ROOT / 'data/air_quality_historical.csv').pm2_5
    wf = pd.read_csv(ROOT / 'results/walkforward_predictions.csv')
    r = validate(g, cams, wf); Path(a.out).write_text(json.dumps(r, indent=2), encoding='utf-8'); print(json.dumps(r, indent=2))
