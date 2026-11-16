"""Reproduce every result:  python run_all.py            (full run)
                           python run_all.py --stage dev  (development folds + frozen selection only)

Protocol (see PROTOCOL.json):
  1. Models are refit monthly on past data only (walk-forward). Every forecast is scored out-of-sample.
  2. DEVELOPMENT window 2023-09-01..2024-12-31 (six chronological blocks) is the ONLY place where the
     forecast model and the uncertainty method are chosen.
  3. 2025 is a KNOWN BENCHMARK: an earlier version of this project already looked at it, so it is reported
     but never used to choose anything.
  4. 2026-01-01..2026-02-18 was never used before this version and is evaluated once, after the choice is frozen.
"""
from pathlib import Path
import argparse, json, hashlib, platform
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from evaluation import *
from model import warning_metrics

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'; OUT.mkdir(exist_ok=True)
T = pd.Timestamp
DEV = (T('2023-09-01'), T('2024-12-31'))
BENCH = (T('2025-01-01'), T('2025-12-31'))
HOLD = (T('2026-01-01'), T('2026-02-18'))
BLOCKS = [('2023 Sep-Nov', '2023-09-01', '2023-11-30'), ('2023-24 Dec-Feb', '2023-12-01', '2024-02-29'),
          ('2024 Mar-May', '2024-03-01', '2024-05-31'), ('2024 Jun-Aug', '2024-06-01', '2024-08-31'),
          ('2024 Sep-Nov', '2024-09-01', '2024-11-30'), ('2024 Dec (partial)', '2024-12-01', '2024-12-31')]


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')


def window_mask(index, lo, hi):
    return np.asarray((index >= lo) & (index <= hi))


def decision_row(actual, score, thr=PRIMARY[0], ratio=PRIMARY[1]):
    m = warning_metrics(actual, score, thr, ratio)
    return {k: m[k] for k in ('fn', 'fp', 'flagged', 'cost')}


def evaluate_window(wf, cal, mask, model, scheme, label, seasonal=None):
    """Everything we report for one frozen (model, scheme) over one window."""
    y = wf.actual.values[mask]
    sc_m, sc_p = cal[(model, scheme)], cal[('Persistence', scheme)]
    valid = sc_m.lo.notna().values[mask] & sc_p.lo.notna().values[mask]
    assert valid.all(), f'{label}: calibration history missing on some days'
    pm, pp = wf[model].values[mask], wf['Persistence'].values[mask]
    rep = {'n': int(mask.sum()), 'forecast': {n: {'mae': mae(y, wf[n].values[mask]), 'rmse': rmse(y, wf[n].values[mask])} for n in SPECS},
           'mae_gain_vs_persistence': float(np.mean(np.abs(y - pp) - np.abs(y - pm))),
           'mae_gain_ci95': block_bootstrap(np.abs(y - pp) - np.abs(y - pm))}
    rep['mae_gain_pct'] = 100 * rep['mae_gain_vs_persistence'] / rep['forecast']['Persistence']['mae']
    rep['interval'] = {'model': cov_width(y, sc_m.lo.values[mask], sc_m.hi.values[mask]),
                       'persistence': cov_width(y, sc_p.lo.values[mask], sc_p.hi.values[mask])}
    if seasonal is not None:
        rep['interval_by_group'] = {g: {'model': cov_width(y[mk], sc_m.lo.values[mask][mk], sc_m.hi.values[mask][mk]),
                                        'persistence': cov_width(y[mk], sc_p.lo.values[mask][mk], sc_p.hi.values[mask][mk])}
                                    for g, mk in seasonal.items() if mk.sum() >= 5}
    rep['decision_primary'] = {
        'Never flag': decision_row(y, np.zeros(len(y))),
        'Always flag': decision_row(y, np.full(len(y), 1e6)),
        'Persistence (raw)': decision_row(y, pp),
        'Persistence + calibrated margin': decision_row(y, sc_p['s3'].values[mask]),
        'Model (raw)': decision_row(y, pm),
        'Model + calibrated margin': decision_row(y, sc_m['s3'].values[mask])}
    rep['decision_sensitivity'] = []
    for thr in THRESHOLDS:
        for r in RATIOS:
            cm = day_costs(y, sc_m[f's{r}'].values[mask], thr, r); cp = day_costs(y, sc_p[f's{r}'].values[mask], thr, r)
            d = cp - cm
            rep['decision_sensitivity'].append({'threshold': thr, 'ratio': r, 'model_cost': float(cm.sum()), 'persistence_cal_cost': float(cp.sum()),
                                                'model_cost_advantage': float(d.sum()), 'advantage_ci95_per_day': block_bootstrap(d),
                                                'high_days': int((y > thr).sum())})
    return rep


def main(stage='full'):
    raw = load_series(ROOT / 'data/air_quality_historical.csv')
    x, y, history, tdates = build_frame(raw)
    last = DEV[1] if stage == 'dev' else tdates.max()
    keep = tdates <= last
    x, y, tdates = x[keep], y[keep], tdates[keep]
    wf = walk_forward(x, y, tdates, history, T('2023-03-01'), last)
    assert wf.index.is_monotonic_increasing and wf.index.is_unique
    assert (wf.origin_date + pd.Timedelta(days=1) == wf.index).all()
    cal = {(m, s): calibrate(wf.index, wf[m].values, wf.actual.values, s) for m in SPECS for s in SCHEMES}
    for k in cal: cal[k].index = wf.index
    dev = window_mask(wf.index, *DEV)

    # ------------------------------------------------------------------ development: choose model
    dev_y = wf.actual.values[dev]
    dev_blocks = {b: window_mask(wf.index, T(a), T(z)) for b, a, z in BLOCKS}
    bl = list(dev_blocks)
    mae_table = {n: {'pooled': mae(dev_y, wf[n].values[dev]), **{b: mae(wf.actual.values[mk], wf[n].values[mk]) for b, mk in dev_blocks.items()}} for n in SPECS}
    wins = {n: int(sum(mae_table[n][b] < mae_table['Persistence'][b] for b in bl)) for n in SPECS}
    chosen = min(FITTED, key=lambda n: mae_table[n]['pooled'])
    best_base = min(BASELINES, key=lambda n: mae_table[n]['pooled'])

    # ------------------------------------------------------------------ development: choose uncertainty method
    seas_dev = {b: mk[dev] for b, mk in dev_blocks.items()}
    scheme_table = {}
    for s in SCHEMES:
        per_block = {b: cov_width(wf.actual.values[mk], cal[(chosen, s)].lo.values[mk], cal[(chosen, s)].hi.values[mk]) for b, mk in dev_blocks.items()}
        full = cov_width(dev_y, cal[(chosen, s)].lo.values[dev], cal[(chosen, s)].hi.values[dev])
        usable = [v for v in per_block.values() if v['n'] >= 25]
        reliability = float(np.mean([abs(v['coverage'] - .8) for v in usable]))
        worst = float(max(abs(v['coverage'] - .8) for v in usable))
        cm = cal[(chosen, s)]; cp = cal[('Persistence', s)]
        dec = {'model': decision_row(dev_y, cm['s3'].values[dev]), 'persistence_cal': decision_row(dev_y, cp['s3'].values[dev])}
        diff = day_costs(dev_y, cp['s3'].values[dev], *PRIMARY) - day_costs(dev_y, cm['s3'].values[dev], *PRIMARY)
        scheme_table[s] = {'overall': full, 'blocks': per_block, 'mean_abs_coverage_error': reliability, 'worst_block_coverage_error': worst,
                           'decision_primary': dec, 'model_cost_advantage': float(diff.sum()), 'advantage_ci95_per_day': block_bootstrap(diff)}
    scheme = min(SCHEMES, key=lambda s: (round(scheme_table[s]['mean_abs_coverage_error'], 3), scheme_table[s]['overall']['width']))

    # ------------------------------------------------------------------ abrupt-change caution flag (dev only decides)
    chg = np.abs(x.pm_change)
    chg_cut = float(chg[(tdates < DEV[0])].quantile(.9))
    wf['abrupt'] = (chg.reindex(wf.origin_date).values > chg_cut)
    ae = np.abs(wf.actual - wf[chosen])

    def abrupt_stats(mk):
        f = wf.abrupt.values[mk]
        return {'abrupt_days': int(f.sum()), 'mae_abrupt': float(ae.values[mk][f].mean()) if f.any() else None,
                'mae_other': float(ae.values[mk][~f].mean())}
    abrupt = {'rule': 'today differs from yesterday by more than the 90th percentile of |daily change| measured before 2023-09-01',
              'cutoff_ug_m3': chg_cut, 'dev': abrupt_stats(dev)}
    abrupt['supported_on_dev'] = bool(abrupt['dev']['mae_abrupt'] > abrupt['dev']['mae_other'])

    frozen = {'forecast_model': chosen, 'forecast_model_config': SPECS[chosen], 'uncertainty_scheme': scheme, 'uncertainty_label': SCHEME_LABEL[scheme],
              'best_baseline_on_dev': best_base, 'primary_threshold': PRIMARY[0], 'primary_cost_ratio': PRIMARY[1],
              'selected_using': f'{DEV[0].date()} to {DEV[1].date()} only', 'refit': 'monthly, expanding window, target dates before the month start',
              'abrupt_flag_supported_on_dev': abrupt['supported_on_dev'], 'abrupt_cutoff': chg_cut}
    frozen['sha256'] = hashlib.sha256(json.dumps(frozen, sort_keys=True).encode()).hexdigest()
    dump('selection_frozen.json', frozen)
    dev_rep = evaluate_window(wf, cal, dev, chosen, scheme, 'dev', seasonal=seas_dev)
    dev_dump = {'mae_by_block': mae_table, 'blocks_beating_persistence': wins, 'schemes': scheme_table, 'selected_window': dev_rep, 'abrupt': abrupt}
    dump('dev_results.json', dev_dump)
    print(f'[dev] chosen model: {chosen} | best baseline: {best_base} | uncertainty scheme: {scheme}')
    for n in SPECS: print(f"   {n:<28} dev MAE {mae_table[n]['pooled']:.2f}  blocks better than persistence: {wins[n]}/{len(bl)}")
    for s in SCHEMES:
        t = scheme_table[s]
        print(f"   {SCHEME_LABEL[s]:<32} cov {t['overall']['coverage']:.3f} width {t['overall']['width']:.1f} mean|cov-.8| {t['mean_abs_coverage_error']:.3f} worst {t['worst_block_coverage_error']:.3f} cost model {t['decision_primary']['model']['cost']:.0f} vs persistence-cal {t['decision_primary']['persistence_cal']['cost']:.0f}")
    print('[dev] decision, chosen scheme:', json.dumps(dev_rep['decision_primary']))
    print('[dev] mae gain', round(dev_rep['mae_gain_pct'], 2), '% CI', dev_rep['mae_gain_ci95'], '| abrupt', json.dumps(abrupt))
    if stage == 'dev':
        return

    # ------------------------------------------------------------------ frozen evaluation: 2025 (known) and 2026 (new)
    bench = window_mask(wf.index, *BENCH); hold = window_mask(wf.index, *HOLD)
    assert bench.sum() == 365 and hold.sum() == 49
    seas_b = {s: np.isin(wf.index[bench].month, ms) for s, ms in SEASONS.items()}
    bench_rep = evaluate_window(wf, cal, bench, chosen, scheme, 'bench', seasonal=seas_b)
    hold_rep = evaluate_window(wf, cal, hold, chosen, scheme, 'hold', seasonal={'Jan-Feb 2026': np.ones(int(hold.sum()), bool)})
    bench_rep['abrupt'] = abrupt_stats(bench); hold_rep['abrupt'] = abrupt_stats(hold)
    abrupt['bench'] = bench_rep['abrupt']; abrupt['hold'] = hold_rep['abrupt']
    full_grid = {}
    for name, mk in (('bench_2025', bench), ('holdout_2026', hold)):
        yy = wf.actual.values[mk]; full_grid[name] = {}
        for m in SPECS:
            for s in SCHEMES:
                c = cal[(m, s)]
                full_grid[name][f'{m} | {s}'] = {'coverage': cov_width(yy, c.lo.values[mk], c.hi.values[mk]), 'decision_primary': decision_row(yy, c['s3'].values[mk])}
    pool = bench | hold; yp = wf.actual.values[pool]; pooled = []
    for thr in THRESHOLDS:
        d = day_costs(yp, cal[('Persistence', scheme)]['s3'].values[pool], thr, 3.) - day_costs(yp, cal[(chosen, scheme)]['s3'].values[pool], thr, 3.)
        pooled.append({'threshold': thr, 'ratio': 3, 'days': int(pool.sum()), 'model_cost_advantage': float(d.sum()), 'advantage_ci95_per_day': block_bootstrap(d)})
    out = {'frozen': frozen, 'pooled_2025_2026_decision': pooled, 'dev': dev_rep, 'benchmark_2025': bench_rep, 'holdout_2026': hold_rep, 'abrupt': abrupt,
           'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__, 'matplotlib': matplotlib.__version__}}
    dump('metrics.json', out); dump('full_grid.json', full_grid)
    dev_dump['abrupt'] = abrupt; dump('dev_results.json', dev_dump)

    # ------------------------------------------------------------------ audit + exports
    audit = {'raw_rows': len(raw), 'raw_start': str(raw.index.min().date()), 'raw_end': str(raw.index.max().date()),
             'raw_sha256': hashlib.sha256((ROOT / 'data/air_quality_historical.csv').read_bytes()).hexdigest(),
             'source_type': 'CAMS modeled estimates (Open-Meteo); NOT ground-sensor measurements',
             'first_walkforward_target': str(wf.index.min().date()), 'last_target': str(wf.index.max().date()),
             'windows': {'development': [str(DEV[0].date()), str(DEV[1].date()), int(dev.sum())], 'benchmark_2025': [str(BENCH[0].date()), str(BENCH[1].date()), int(bench.sum())],
                         'holdout_2026': [str(HOLD[0].date()), str(HOLD[1].date()), int(hold.sum())]},
             'daily_timezone': 'Not documented in the uploaded dataset.',
             'forecast_issue_times': 'Not available: retrospective dated-series evaluation, not a certified operational backtest.'}
    dump('audit.json', audit)
    flagcol = {}
    for tag, m in (('model', chosen), ('persistence', 'Persistence')):
        c = cal[(m, scheme)]
        for k in ['lo', 'hi', 's1', 's3', 's5']: flagcol[f'{tag}_{k}'] = c[k].values
    exp = pd.DataFrame({'origin_date': wf.origin_date.dt.strftime('%Y-%m-%d'), 'target_date': wf.index.strftime('%Y-%m-%d'), 'actual': wf.actual.values,
                        **{n: wf[n].values for n in SPECS}, 'abrupt_change_today': wf.abrupt.values.astype(int), **flagcol})
    exp.to_csv(OUT / 'walkforward_predictions.csv', index=False, float_format='%.6g')
    ev = bench | hold
    exp[ev].assign(absolute_error=ae.values[ev]).nlargest(10, 'absolute_error')[['origin_date', 'target_date', 'actual', chosen, 'Persistence', 'absolute_error']].to_csv(OUT / 'largest_errors.csv', index=False, float_format='%.6g')
    x.to_csv(OUT / 'features.csv', index_label='origin_date', float_format='%.8g')
    plots(wf, cal, chosen, scheme, mae_table, scheme_table, bench_rep, hold_rep, bench, dev_blocks)
    print('[bench 2025] MAE gain %', round(bench_rep['mae_gain_pct'], 2), bench_rep['mae_gain_ci95'], json.dumps(bench_rep['decision_primary']))
    print('[hold 2026]  MAE gain %', round(hold_rep['mae_gain_pct'], 2), hold_rep['mae_gain_ci95'], json.dumps(hold_rep['decision_primary']))
    print('[hold 2026 MAE]', {n: round(hold_rep['forecast'][n]['mae'], 2) for n in SPECS})
    print('[bench 2025 MAE]', {n: round(bench_rep['forecast'][n]['mae'], 2) for n in SPECS})
    print('[bench interval]', json.dumps(bench_rep['interval']), json.dumps({g: v['model'] for g, v in bench_rep['interval_by_group'].items()}))
    print('[hold interval]', json.dumps(hold_rep['interval']))
    print('[sensitivity bench]', [(r['threshold'], r['ratio'], r['model_cost'], r['persistence_cal_cost']) for r in bench_rep['decision_sensitivity']])
    print('[sensitivity hold]', [(r['threshold'], r['ratio'], r['model_cost'], r['persistence_cal_cost']) for r in hold_rep['decision_sensitivity']])
    print('[abrupt]', json.dumps(abrupt))


def plots(wf, cal, chosen, scheme, mae_table, scheme_table, bench_rep, hold_rep, bench, dev_blocks):
    plt.rcParams.update({'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False})
    bl = list(dev_blocks)
    fig, ax = plt.subplots(figsize=(11, 5))
    names = [n for n in SPECS if n != 'Persistence']; w = .8 / len(names)
    for i, n in enumerate(names):
        ax.bar(np.arange(len(bl)) + i * w, [100 * (1 - mae_table[n][b] / mae_table['Persistence'][b]) for b in bl], w, label=n, color=plt.cm.tab20(i))
    ax.axhline(0, color='k', lw=.8); ax.set_xticks(np.arange(len(bl)) + .4, bl, rotation=15)
    ax.set_ylabel('MAE improvement over persistence (%)'); ax.set_title('Development blocks: which forecasts beat "tomorrow = today"?')
    ax.legend(fontsize=7.5, ncol=2, frameon=False); fig.tight_layout(); fig.savefig(OUT / 'model_comparison.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
    for i, s in enumerate(SCHEMES):
        cov = [scheme_table[s]['blocks'][b]['coverage'] for b in bl]
        ax[0].plot(range(len(bl)), cov, marker='o', label=SCHEME_LABEL[s], lw=2.6 if s == scheme else 1, color=plt.cm.tab10(i))
    ax[0].axhline(.8, color='k', ls='--', lw=1); ax[0].set_xticks(range(len(bl)), bl, rotation=25, ha='right', fontsize=8)
    ax[0].set(ylabel='coverage of nominal 80% interval', title='Development: coverage by block (bold = chosen)'); ax[0].legend(fontsize=7, frameon=False, loc='lower left')
    cats = ['Persistence (raw)', 'Persistence + calibrated margin', 'Model (raw)', 'Model + calibrated margin']
    xs = np.arange(len(cats)); width = .38
    for k, (rep, nm, col) in enumerate(((bench_rep, '2025 known benchmark', '#64748b'), (hold_rep, 'Jan-Feb 2026 new holdout', '#0d9488'))):
        ax[1].bar(xs + (k - .5) * width, [rep['decision_primary'][c]['cost'] / rep['n'] for c in cats], width, label=nm, color=col)
    ax[1].set_xticks(xs, [c.replace(' + ', '\n+ ') for c in cats], fontsize=8)
    ax[1].set_ylabel('illustrative cost per day'); ax[1].set_title('Warning cost at 55 µg/m³, 3:1 (lower is better)'); ax[1].legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / 'decision_comparison.png', dpi=160); plt.close(fig)
    c = cal[(chosen, scheme)]; d = pd.to_datetime(wf.index[bench])
    fig, ax = plt.subplots(figsize=(12, 4.6))
    ax.fill_between(d, c.lo.values[bench], c.hi.values[bench], color='#0d9488', alpha=.15, label=f'80% interval ({SCHEME_LABEL[scheme]})')
    ax.plot(d, wf.actual.values[bench], color='#172554', lw=1.1, label='CAMS reference'); ax.plot(d, wf[chosen].values[bench], color='#0d9488', lw=1, label=chosen)
    ax.set(ylabel='daily mean PM2.5 (µg/m³)', title='2025 walk-forward forecasts (known benchmark)'); ax.legend(ncol=3, loc='upper left', frameon=False)
    fig.tight_layout(); fig.savefig(OUT / 'forecast.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--stage', choices=['dev', 'full'], default='full')
    main(ap.parse_args().stage)
