# What remains blocked by missing evidence

The new weather/probability work is complete on supplied files. No real monitor measurements, archived issue-time CAMS forecast, other-city series, or stakeholder responses were supplied. Do not mark these as completed.

## 1. Lahore ground measurements
Verified source leads on November16,2026:
- EPA embassy map: https://gispub.epa.gov/OAR_OAQPS/airnowembassy/ — documents reference-grade stations and historical archives; current/preliminary readings are not final QA.
- OpenAQ Lahore diplomatic station: https://explore.openaq.org/locations/8664 — reference-grade PM2.5, StateAir Lahore. Its page reports an old last update, so do not assume 2025/26 coverage.
- The older AirNow international page returned404. The map's documentation is not proof that a specific yearly Lahore download remains available. Local downloads from the research runtime failed DNS.

Needed: one station's **hourly raw PM2.5 concentration in µg/m³**, timestamps, timezone, QC flags, station identifier, coordinates, source/license and overlapping dates. Do not supply AQI or a NowCast index as concentration.

`prepare_ground.py` now requires explicit input and aggregation timezones, rejects duplicate hours, removes negative missing codes, and counts actual unique hours. Apply the source's QC flags first. Example (replace column names with those in the real file):
```
python prepare_ground.py monitor.csv --time-col timestamp --value-col pm25 --input-timezone Asia/Karachi --daily-timezone UTC --out ground_daily.csv
python validate_ground.py --ground ground_daily.csv --time-col date --value-col pm2_5
```
The legacy validator scores Claude's baseline forecasts. Re-scoring the new research outputs needs an explicit aligned merge once real data are supplied; no results should be fabricated. The pollution archive's day boundary is undocumented. Compare prescribed UTC/local alignments transparently or resolve the source definition; never choose the best shift on the test data and present it as an established timezone.

## 2. Actual day-ahead weather
The supplied export has UTC hourly values but no initialization time, lead time, forecast model or boundary-layer height. It cannot prove what was known one day ahead. The implementation uses a conservative one-day weather lag.

Open-Meteo explains that its Historical Forecast API stitches early hours of model runs. For fixed lead-time assessment use Previous Runs (`_previous_day1` etc.) or explicit Single Runs:
- https://open-meteo.com/en/docs/historical-forecast-api
- https://open-meteo.com/en/docs/previous-runs-api

A `_previous_day1` value is24 hours before each valid hour, not necessarily a single common initialization before the start of the whole target day. For a next-day daily forecast, choose a common issue cutoff and ensure **all** target-day hours were available by that cutoff. Keep initialization and valid times. Do not substitute target-day reanalysis for those forecasts.

## 3. Direct CAMS forecast comparator
Official archived forecast dataset: https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts (DOI10.24381/04a0b097; portal login/download workflow). CAMS archives preserve forecasts; the plain air-quality daily series currently bundled does not preserve a verifiable issue-time/lead-time mapping.

Needed fields: initialization/issue timestamp, valid timestamp, lead time, PM2.5, units, grid coordinates, model/version/source. Extract Lahore and a fixed forecast issue schedule. Many model exports use mass concentration units different from µg/m³: inspect metadata before converting. Prefer independent ground truth as the verification target. No evidence has been produced that SmogWindow beats CAMS's own issued forecast.

## 4. Real stakeholder
Use the existing `STAKEHOLDER_REVIEW.md` with an actual teacher or sports coordinator. Record consent, their role, the decision time, current process, applicable school/official guidance and their acceptable trade-off. Separate a participant's preference from a legal/medical standard. The current55 µg/m³ threshold and3:1 cost are illustrative. No interview, quote, partnership or cost estimate has been invented.

## 5. Other-city transfer
A same-source Karachi dataset is listed at https://zenodo.org/records/18673762. Verify its files, license and coverage before use. This would test spatial transfer of CAMS-series modeling, not independently measured accuracy. No Islamabad dataset was verified in this check.

For a strict transfer test, fit in Lahore and freeze coefficients/features/calibration before seeing another city's outcomes. Report zero-shot transfer separately from any local refit. Obtain weather from the same product/timing convention if testing weather features. Do not quietly retrain in Karachi and call that frozen transfer.

## Competition timing
The published deadline was November16,2026 at9:59 a.m.Pakistan time. This revision was built afterward. It is research/portfolio work unless the organizer explicitly allows a later version. Do not claim these changes were in a previously submitted entry.
