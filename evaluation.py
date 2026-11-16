"""Walk-forward evaluation, uncertainty calibration schemes and scoring. NumPy/pandas only."""
import numpy as np
import pandas as pd
from model import features, fit_model, predict, columns_for, climatology, warning_metrics

RATIOS = (1, 3, 5)
THRESHOLDS = (35, 55, 100)
PRIMARY = (55., 3.)  # fixed before any evaluation; illustrative, not a regulation
SEASONS = {'Winter': [12, 1, 2], 'Spring': [3, 4, 5], 'Summer': [6, 7, 8], 'Autumn': [9, 10, 11]}

# Every candidate is scored on identical rows. 'baseline' entries use no fitted parameters.
SPECS = {
    'Persistence':            {'kind': 'persistence'},
    'Trailing 7-day mean':    {'kind': 'mean7'},
    'Seasonal climatology':   {'kind': 'climatology'},
    'Persistence+climate 50/50': {'kind': 'blend'},
    'Ridge minimal (a=100)':  {'kind': 'ridge', 'alpha': 100, 'features': 'minimal'},
    'Ridge history (a=100)':  {'kind': 'ridge', 'alpha': 100, 'features': 'history'},
    'Ridge history (a=1000)': {'kind': 'ridge', 'alpha': 1000, 'features': 'history'},
    'Log-ridge history (a=100)':  {'kind': 'ridge', 'alpha': 100, 'features': 'history', 'log': True},
    'Log-ridge history (a=1000)': {'kind': 'ridge', 'alpha': 1000, 'features': 'history', 'log': True},
    'Ridge full (a=1000)':    {'kind': 'ridge', 'alpha': 1000, 'features': 'full'},
    'Boosted stumps (150)':   {'kind': 'stumps', 'steps': 150, 'features': 'full'},
}
BASELINES = [k for k, v in SPECS.items() if v['kind'] in ('persistence', 'mean7', 'climatology', 'blend')]
FITTED = [k for k in SPECS if k not in BASELINES]
SCHEMES = ['global_abs', 'global_signed', 'trail90', 'trail180', 'level_bins', 'log_relative']
SCHEME_LABEL = {'global_abs': 'All-past |error| (v1 style)', 'global_signed': 'All-past signed errors',
                'trail90': 'Trailing 90 days', 'trail180': 'Trailing 180 days',
                'level_bins': 'By forecast level (terciles)', 'log_relative': 'Relative (log-scale) errors'}


def load_series(path):
    raw = pd.read_csv(path, parse_dates=['date']).set_index('date').sort_index()
    assert raw.index.is_unique
    assert (raw.select_dtypes('number').dropna() >= 0).all().all()
    # The first non-null day looks like a partial day of averaging; excluded conservatively (inference).
    raw.loc[pd.Timestamp('2022-08-04'), :] = np.nan
    return raw


def build_frame(raw):
    x, y, history = features(raw)
    good = x.notna().all(axis=1) & y.notna()
    x = x.loc[good]; y = y.loc[good]
    tdates = x.index + pd.Timedelta(days=1)
    return x, y, history, pd.DatetimeIndex(tdates)


def walk_forward(x, y, tdates, history, first, last, specs=SPECS):
    """Operational simulation. Models are refit at the start of each month using only rows whose target
    date is before that month. Nothing dated on/after the forecast's origin informs its model."""
    sel = np.where((tdates >= first) & (tdates <= last))[0]
    months = pd.PeriodIndex(tdates[sel], freq='M')
    out = pd.DataFrame({'origin_date': x.index[sel], 'actual': y.values[sel]}, index=tdates[sel])
    for name in specs:
        out[name] = np.nan
    for m in months.unique():
        te = sel[np.asarray(months == m)]
        tr = np.where(tdates < m.start_time)[0]
        assert len(tr) >= 120, 'not enough history to fit'
        clim = climatology(tdates[tr], y.values[tr], tdates[te])
        for name, sp in specs.items():
            k = sp['kind']
            if k == 'persistence': p = x.pm_lag_0.values[te]
            elif k == 'mean7': p = x.pm_mean_7.values[te]
            elif k == 'climatology': p = clim
            elif k == 'blend': p = .5 * x.pm_lag_0.values[te] + .5 * clim
            else:
                cols = columns_for(sp, list(x.columns), history)
                mod = fit_model(x.iloc[tr][cols], y.iloc[tr], sp)
                p = predict(mod, x.iloc[te])
            out.loc[tdates[te], name] = p
    return out


def _q(a, level, method):
    return float(np.quantile(a, level, method=method))


def calibrate(dates, pred, actual, scheme, min_hist=120):
    """For each day, build an 80% interval and warning scores (for miss:false-alarm cost ratios 1, 3, 5)
    from errors of EARLIER days only (target date <= today-1). Returns a DataFrame; NaN until enough history."""
    dates = np.asarray(dates, 'datetime64[D]'); pred = np.asarray(pred, float); actual = np.asarray(actual, float)
    n = len(pred); res = actual - pred; rel = np.log1p(actual) - np.log1p(pred)
    cols = ['lo', 'hi'] + [f's{r}' for r in RATIOS]
    out = np.full((n, len(cols)), np.nan)
    window = {'trail90': 90, 'trail180': 180}.get(scheme)
    need = min(min_hist, int(.66 * window)) if window else min_hist
    for i in range(n):
        j = np.searchsorted(dates, dates[i] - np.timedelta64(1, 'D'), side='right')
        j0 = np.searchsorted(dates, dates[i] - np.timedelta64(window, 'D'), side='left') if window else 0
        if j - j0 < need:
            continue
        p = pred[i]; r = res[j0:j]
        if scheme == 'log_relative':
            e = rel[j0:j]; base = np.log1p(p)
            lo = np.expm1(base + _q(e, .1, 'lower')); hi = np.expm1(base + _q(e, .9, 'higher'))
            sc = [np.expm1(base + _q(e, c / (1 + c), 'higher')) for c in RATIOS]
        else:
            if scheme == 'level_bins':
                ph = pred[j0:j]; cuts = np.quantile(ph, [1 / 3, 2 / 3])
                m = np.digitize(ph, cuts) == np.digitize(p, cuts)
                if m.sum() >= 30: r = r[m]
            if scheme == 'global_abs':
                m = len(r); level = min(1, np.ceil((m + 1) * .8) / m); rad = _q(np.abs(r), level, 'higher')
                lo, hi = p - rad, p + rad
            else:
                lo, hi = p + _q(r, .1, 'lower'), p + _q(r, .9, 'higher')
            sc = [p + _q(r, c / (1 + c), 'higher') for c in RATIOS]
        out[i] = [max(0., lo), hi] + sc
    return pd.DataFrame(out, columns=cols)


def mae(a, b): return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))
def rmse(a, b): return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def cov_width(actual, lo, hi):
    ok = np.isfinite(lo)
    if not ok.any(): return {'coverage': None, 'width': None, 'n': 0}
    a = np.asarray(actual)[ok]
    return {'coverage': float(np.mean((a >= lo[ok]) & (a <= hi[ok]))), 'width': float(np.mean(hi[ok] - lo[ok])), 'n': int(ok.sum())}


def day_costs(actual, score, threshold, ratio):
    """Per-day cost: ratio per missed high day, 1 per false alarm."""
    a = np.asarray(actual) > threshold; f = np.asarray(score) > threshold
    return ratio * (a & ~f).astype(float) + (~a & f).astype(float)


def block_bootstrap(diff, block=7, n=2000, seed=26080):
    """Circular moving-block bootstrap of the mean of a paired per-day difference."""
    diff = np.asarray(diff, float); m = len(diff); rng = np.random.default_rng(seed)
    nb = int(np.ceil(m / block)); means = []
    for _ in range(n):
        s = rng.integers(0, m, size=nb)
        ix = np.concatenate([(k + np.arange(block)) % m for k in s])[:m]
        means.append(diff[ix].mean())
    return [float(v) for v in np.quantile(means, [.025, .975])]


def season_of(dates):
    mo = pd.DatetimeIndex(dates).month
    return np.array([[s for s, ms in SEASONS.items() if m in ms][0] for m in mo])
