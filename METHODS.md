# Method and evaluation record (version 2)

## Data and limits
Zenodo DOI 10.5281/zenodo.18673725 (supplied as `lahore-pk-1172451.zip`): 1,298 daily rows, 2022-08-01 to 2026-02-18, gridded CAMS estimates served by Open-Meteo for 31.558, 74.35071. These are **model estimates, not measurements**; they do not establish school-site exposure or agreement with any monitor. Daily timezone, hourly completeness and forecast issue times are undocumented, so this is a retrospective dated-series evaluation, not a certified operational backtest. Three null days and the first non-null day (which looks like a partial day; an inference) are excluded. Original CSV SHA256: `ce1327775720bae72986a04edeab0cfdce0f778642be499570bdf8e6d152b0fb`.

## Information boundary
For origin date t, every input is dated t or earlier and the target is the next dated day's mean PM2.5. This assumes day t's aggregate is already complete. Features: PM2.5 lags 0,1,2,3,6,13; trailing means/SDs (3,7,14 days); one-day change; annual and semiannual calendar terms for the target day; for "full" models also today's and yesterday's PM10, CO, NO2, SO2, ozone, aerosol optical depth, dust, UV index. The calendar is reindexed before shifting so a gap cannot become a silent one-day forecast.

## Walk-forward protocol (new in v2)
Instead of one frozen split, every model is refit on the first day of each month from 2023-03 onward, using only rows whose target date is earlier. This simulates operation and gives 1,000+ out-of-sample forecasts across seasons. Windows:
- **Development** 2023-09-01..2024-12-31 (488 days, six chronological blocks): the only place a choice is made.
- **2025 (known benchmark, 365 days):** an earlier version had already examined 2025, so it is NOT untouched. It is reported, never tuned on.
- **Jan 1 - Feb 18, 2026 (new holdout, 49 days):** unused before this version; evaluated after the selection was written. It is winter and only 49 days: informative but statistically thin.

## Candidates (11, all scored on identical rows)
Baselines: persistence; trailing 7-day mean; seasonal climatology (+-15 days, from earlier years only); 50/50 persistence-climatology blend. Fitted: ridge on 5 minimal features (alpha 100); ridge on 17 history features (alpha 100, 1000); the same on log scale (alpha 100, 1000); ridge on all 33 features (alpha 1000); 150 boosted depth-one trees on all features. Ridge/tree models learn the change from persistence (log-ratio for log models). Rule fixed in advance: the fitted candidate with the lowest pooled development MAE. Result: **ridge, all features, alpha 1000.** Several candidates are within about 2% of it; the selection should not be read as proof that pollutant features matter.

## Uncertainty (new in v2)
Six ways to turn earlier errors into an 80% interval and a cost-weighted warning margin: all-past absolute errors (the v1 method), all-past signed errors, trailing 90 days, trailing 180 days, errors grouped by forecast-level tercile, and relative (log-scale) errors. For each forecast day only errors of earlier target dates are used. Rule fixed in advance: the smallest average gap between observed and nominal 80% coverage across the development blocks. Result: **relative (log-scale) errors** (mean gap 5.3 points, worst block 12.3, versus 13.7 / 25.2 for the v1 method). Because winter errors are larger in absolute terms, scaling errors by level is a plausible reason; the data cannot prove the mechanism. The same method is applied to persistence so the comparison isolates what the ML forecast adds.

## Warning policy
Flag when forecast + the c/(c+1) quantile of earlier errors exceeds the threshold. Primary setting (55 ug/m3, c = 3) was fixed before any evaluation and is illustrative, not a regulation. Cost = c x missed high days + false alarms; not money or health impact.

## Statistics
Paired circular moving-block bootstrap (7-day blocks, 2,000 resamples, seed 26080) for the MAE gain and for the cost difference. The intervals are descriptive and uncorrected for the many settings displayed; across thresholds/ratios some intervals touch zero and a few exclude it by small margins.

## Abrupt-change caution flag
Rule (fixed on pre-development data): today differs from yesterday by more than 34.5 ug/m3 (90th percentile of absolute daily change before 2023-09). Selected for display because MAE after such days was higher in development (27.5 vs 11.0) and 2025 (17.3 vs 12.5), but it reversed in Jan-Feb 2026 (19.5 vs 23.9, 14 days). Treat as weak evidence.

## Tests (`test_integrity.py`)
Future-mutation and prefix invariance of features; walk-forward forecasts unchanged when all data after a cut-off are destroyed; calibration for day i unchanged when day-i-and-later actuals are destroyed (6 methods); **selection identical when 2025-2026 are deleted**; window boundaries and alignment; dashboard data parity; operational forecast ignores later data and refuses on gaps; ground-validation tool on SYNTHETIC test data (never reported); Open-Meteo parser on a mock response.

## Ground validation
No ground-monitor data were available in the build environment; the independent validation is NOT done. `validate_ground.py` and `data/GROUND_DATA_GUIDE.md` are ready for when a real file is obtained.

## Honest conclusion
1. The ML forecast is modestly but consistently more accurate than persistence on modeled data (3.4% development, 8.1% in 2025, 7.0% in the 2026 holdout).
2. Learned error margins, not the ML forecast, do most of the work in warnings.
3. With identical calibration, the model's warnings never cost more than persistence's in the 9 threshold/cost settings for either 2025 or 2026 (cost was lower in 14 of 18 and tied in 4), but the differences are small and mostly not distinguishable from zero. In the development window the sign was mixed (2 of 9 settings favoured persistence). We cannot claim the ML warning system is better.
4. Relative-error calibration repairs most of the winter coverage failure seen in v1 (winter 2025: 76% vs 62%), but intervals still under-cover during sharp winter transitions (Dec 2024: 68%, Jan-Feb 2026: 76%).
5. Nothing has been validated against real monitors, a school, or a live workflow.
