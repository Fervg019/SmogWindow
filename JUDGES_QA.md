# Explain it in your own words (version 2)

Read the code, open the dashboard and run `python run_all.py` before you submit. AI assistance is allowed, but you must understand what you submit.

**What is the AI?** Ridge regression learns a *correction to "tomorrow = today"* from recent PM2.5, rolling statistics, calendar terms and other pollutants. Weights are learned from earlier days only; the model is refit monthly.

**What is new compared with the tutorial project?** The question: does ML improve the *decision* a school makes? Plus a stricter evaluation (walk-forward, development-only selection, a known benchmark and a new holdout), a fair equally calibrated persistence baseline, six uncertainty methods compared, and a decision dashboard.

**Why isn't 2025 a clean test?** An earlier version of this project examined 2025, so it is a known benchmark. Nothing in this version is selected on it, and a test deletes 2025–26 and checks the selection is unchanged. The clean test is Jan 1–Feb 18, 2026 (49 days, never used before): useful but short and all winter.

**Did ML help?** Forecast: yes, modestly and consistently (3.4% development, 8.1% in 2025, 7.0% in 2026; 95% ranges exclude zero but are close to it for development and 2026). Warnings: its advantage over *equally calibrated persistence* is small and mostly within noise (2025: +3 cost units, range −13 to +21). The learned margin, not the ML, drives most of the improvement over raw persistence.

**Why not a bigger model?** About 1,000 daily rows and strong persistence. Boosted stumps and other variants were within roughly 2% of ridge on development data. Complexity is not evidence.

**What is MAE?** Average absolute error in µg/m³ (12.92 is not 12.92%).

**What is the 80% range and why trust it?** Errors from earlier days set how wide the range is. In 2025 it covered 79.5% (winter 76%, autumn 91%) and 75.5% in Jan–Feb 2026. It is not a guarantee and still under-covers sharp winter changes (Dec 2024: 68%).

**Why relative (log-scale) errors?** It was the method with the smallest gap between actual and nominal 80% coverage across the development blocks. A plausible reason is that errors scale with pollution level, but I haven't proven that mechanism.

**Where do 55 and 3:1 come from?** Illustrative, fixed in advance; not regulations or measured school costs. The dashboard lets you change them and shows what changes. Controls re-read results; they do not retune.

**Are these measurements?** No. CAMS model estimates. Ground-monitor validation is not done; the tool (`validate_ground.py`) and a data guide are ready.

**Is it live?** No. The dashboard replays history. `plan_live.py` can issue a forecast from a history file, and `fetch_open_meteo.py` is written to produce fresh rows, but the Open-Meteo fetch could not be tested without network access, and no live feed is running.

**What about the caution flag for abrupt changes?** After a >34.5 µg/m³ day-to-day change, errors were bigger in development and 2025 but not in Jan–Feb 2026. Weak evidence, shown only as a caution.

**Has a school validated it?** No. `STAKEHOLDER_REVIEW.md` is a plan for a short review that has not happened.

**What did the AI tools do?** ChatGPT/Codex and Claude assisted with design, code, tests and writing. Describe your own contribution accurately; do not claim unaided authorship.

**What would you do next?** Get a real monitor's data and run `validate_ground.py`; do a short review with a sports coordinator; evaluate on days that have not happened yet.
