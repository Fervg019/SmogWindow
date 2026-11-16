# SmogWindow weather and probability research update

This revision tests the proposed upgrades on the supplied files. It is post-deadline research. Both 2025 and January 2026 had already been inspected; neither is a new untouched holdout. Targets remain CAMS modeled concentrations, not measurements.

## What changed

- Audited 31,152 UTC weather hours (1,298 complete days), added 12 lagged daily weather features, and compared matched ridge models with and without weather.
- Tested conditional empirical predictive distributions built from historical next-day changes. These produce quantiles and exceedance probabilities directly, replacing the dashboard's error-margin approach in the new research view.
- Selected model settings using September 2023-December 2024 development data; saved a selection lock before scoring known benchmarks. Fits expand monthly with training targets strictly before the test month.
- Added CRPS, quantile pinball losses, interval scores, Brier scores, reliability diagrams and warning-cost sensitivity against empirical persistence, always-flag and never-flag strategies.
- Added conditional analyses for season, prior abrupt changes, lagged rain/wind and retrospective spike days. Added a timezone-explicit monitor preprocessing helper; no monitor observations are bundled.

## Main results

| Metric | Known 2025 (365 days) | Known January 2026 (31 days) |
|---|---:|---:|
| Persistence MAE | 14.05 | 27.32 |
| No-weather ridge MAE | 12.92 | 25.56 |
| Weather ridge MAE | 12.81 | 25.46 |
| Selected probability model CRPS | 9.88 | 18.88 |
| Empirical persistence CRPS | 10.64 | 20.58 |
| Nominal 80% interval coverage | 77.8% | 61.3% |

MAE and CRPS use ug/m3; lower is better. The probability model is a 60-neighbor history-only analog model, selected by development CRPS. Adding weather did not win development selection, so the displayed probabilistic model does not use it. Point ridge and probabilistic median are distinct outputs.

Weather reduces 2025 MAE by 0.111 ug/m3 relative to matched no-weather ridge. The paired seven-day block bootstrap 95% interval is [-0.049, 0.278], including zero. The weather model beats persistence by 8.85%, but this does not establish that weather itself adds a robust gain. January weather improvement is 0.092, interval [-0.217, 0.389].

The selected probability model improves 2025 CRPS by 7.10%, with paired reduction interval [0.429, 1.102]. January's reduction interval [-0.547, 4.493] includes zero. January undercoverage is substantial: only 19 of 31 outcomes fall in the nominal 80% interval. Thirty of those days exceed 55, so this period offers little evidence about false alarms. Improved CRPS is not proof of reliable warnings or health benefit.

In 2025, weather helps more in winter (MAE 21.21 to 20.73) and following abrupt changes (17.13 to 16.89), but slightly worsens rainy-day and realized-spike errors. These overlapping diagnostics do not establish a new decision rule. Realized spikes are known only afterward. No subgroup tuning was used to change the selected models.

## Timing and leakage limits

The weather CSV has no forecast initialization, lead time, product ID or boundary-layer height. It cannot establish genuine day-ahead weather availability. We use the entire UTC day before the forecast origin, excluding origin-day and target-day weather. The underlying pollution archive's daily boundary remains undocumented. This is conservative research alignment, not an audited operational issue-time system. February 2026 is excluded from primary scoring because of archive-end provenance concerns.

Parameters were selected on development data, but the design was made after previous benchmark inspection. Block-bootstrap intervals describe sampled paired errors; they do not remove this researcher exposure, model-source bias or distribution shift. There is one location and no independent target.

## Reproduce

From this folder, install requirements, then run:

```powershell
python test_weather_research.py
python weather_research.py --stage develop
python weather_research.py --stage evaluate
python build_research_report.py
python build_weather_dashboard.py
```

Open `SmogWindow_Weather_dashboard.html`. Computed outputs are already included. Use the CSVs and `weather_metrics.json` to audit every reported value. Thresholds 35/55/100 and missed-event costs 1/3/5 are illustrative, not stakeholder-approved or medical advice.

## Still missing

Real hourly monitor validation, a verifiable issue-time CAMS forecast comparator, an actual stakeholder interview and frozen other-city transfer remain unperformed. See `DATA_NEEDED.md` for source leads and exact required fields. Nothing in this update establishes superiority to CAMS's own forecast or validates school safety decisions.

The original Claude dashboard, notebook, metrics and documents are retained for traceability. Their earlier holdout or submission language does not describe this new revision. AI assistance: Anthropic Claude and ChatGPT/Codex.
