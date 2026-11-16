# Verification record (version 2)

Done in the build environment (Linux, Python 3.13, NumPy/pandas/matplotlib):
- `run_all.py` completes; `test_integrity.py` passes all 10 groups, including: no future data in features; walk-forward forecasts unchanged when later data are destroyed (all 11 candidates); calibration unchanged when later actuals are destroyed (6 methods); **selection hash identical when 2025–26 are deleted**; window boundaries (365 + 49 days); dashboard data parity; operational forecast ignores later data and refuses on a gap; ground-validation tool on **synthetic** data (test only, never reported); Open-Meteo parser on a **mock** response.
- The dashboard was opened in headless Chromium at desktop and 390 px widths: no console errors, no horizontal overflow, date/threshold/cost controls, reveal toggle, "jump to a missed spike", window selector, .txt download and keyboard arrows all exercised. It was not tested in Safari/Firefox or on a physical phone.
- The notebook was executed top to bottom with outputs saved.

Not done: ground-monitor validation (no data available); stakeholder review; live Open-Meteo fetch (no network in the build environment); any upload, recording or submission.
