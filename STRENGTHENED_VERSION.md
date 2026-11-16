# Stronger demonstration, with the same honest evidence

## What is new

The dashboard now includes a 30-day history plot and a next-day forecast interval, a selectable rolling interval adjustment, and an interactive 2025 warning-cost audit. Changing the concentration threshold or missed-event cost shows missed events, false alarms, and comparisons with raw persistence, always flag and never flag. Raw persistence is deliberately labelled: it is not the calibrated persistence comparator from the earlier study.

The rolling interval adjustment uses only already observed target outcomes, a maximum 60-day trailing window, and at least 30 prior errors. The 60-day window was selected from 60/90/180 using development-period interval score. It does not change the median or recalibrate probabilities. Dependence and distribution shift mean it has no demonstrated 80% coverage guarantee.

| Known benchmark | Original coverage | Adjusted coverage | Original width | Adjusted width | Original interval score | Adjusted interval score |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 77.8% | 83.0% | 38.47 | 47.09 | 67.05 | 67.29 |
| January 2026 | 61.3% | 67.7% | 67.86 | 75.80 | 116.99 | 110.68 |

Widths and scores are in ug/m3. Lower interval scores are better. Coverage improves at the expense of width; the full 2025 score gets slightly worse. January remains under-covered. Therefore the original interval remains the default and adjustment is offered as a transparent experiment. This study was designed after seeing these benchmark periods; it is not a fresh holdout evaluation.

## A focused demonstration

1. Open START_WEATHER_DEMO.bat. Explain the specific task: exploring tomorrow's outdoor-activity contingency planning in Lahore.
2. Choose a historical date. Show available history, predicted median, interval and modeled exceedance probability before revealing the future.
3. Reveal the next-day CAMS reference. Explain that this demonstrates a historical forecast, not a live sensor reading.
4. Switch the interval method. Explain the coverage/width trade-off and January failure honestly.
5. Change the assumed threshold and cost. Show how warning performance compares with simple strategies. Do not present an assumed preference as a teacher's recommendation.
6. Finish with evidence: weather's incremental gain is uncertain; probability scoring improved in 2025; independent-monitor and stakeholder validation are still absent.

## Reproduction

After the existing weather development and evaluation commands, run:
```
python strengthen.py
python build_research_report.py
python build_weather_dashboard.py
```
`strengthen.py` includes a future-outcome mutation check: changing the current and later outcomes cannot change the interval available for the current prediction. Full calibration results and per-day values are in research_results/interval_calibration.json and calibrated_intervals.csv.

This revision uses only the existing data. No invented monitor measurements, stakeholder quotes, extrapolated evaluation targets or claimed external validation were added.
