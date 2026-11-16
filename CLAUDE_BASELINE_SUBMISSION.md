# SmogWindow: do better forecasts make better school air-quality warnings?
**Track:** AI + Climate  
**Team:** Muhammad Fasih Ajmal (solo), The City School Ravi Campus

## The problem
A Lahore school sports coordinator must decide whether to prepare an indoor plan before pollution arrives. A single forecast number hides uncertainty, and a clever model may do no better than "tomorrow equals today". I asked whether machine learning improves the *decision*, not just the forecast.

## What I built
A forecasting experiment and an offline browser dashboard. Input: a day's pollution history. Output: next-day PM2.5 forecast, an 80% range, a planning flag, a side-by-side comparison with persistence, data-quality warnings, a track record with uncertainty, and an exportable planning summary. `plan_live.py` issues the same forecast from any history file. It is a research prototype on modeled data, not live monitoring or medical advice.

## What I added
Starting from suggested project 4.3.2, I added the school decision scenario; a stricter walk-forward evaluation (models refit monthly; model and uncertainty method chosen on development data only, with a test that proves it); an equally calibrated persistence comparator; seasonal reliability diagnostics; the dashboard; and ready-to-run ground-validation tooling.

## How it works
Data: 1,298 daily CAMS-modeled PM2.5 and pollutant values for Lahore (Aug 2022–Feb 2026, Zenodo), not sensor measurements. Eleven forecasts were compared (persistence, 7-day mean, climatology, a blend, five ridge variants, boosted stumps) in six chronological development blocks (Sep 2023–Dec 2024). The best fitted model, a ridge regression that learns a correction to persistence, was chosen there, along with a relative-error method for the uncertainty range. Warnings add an error margin learned from earlier forecast errors; the same procedure is applied to persistence.

## Results
Forecast error (MAE, µg/m³), persistence → model: development 12.47 → 12.04 (3.4%); **2025 14.05 → 12.92 (8.1%)**; **new Jan–Feb 2026 holdout 24.35 → 22.64 (7.0%)**. 2025 is a *known* benchmark that an earlier version had examined, so nothing was tuned on it; 2026 was never used before. Learned margins cut missed high days in 2025 from 37 to 15, but calibrated persistence did the same (15 misses, 72 false alarms vs 69). With identical calibration, the model's advantage in warning cost was small and not statistically distinguishable from zero (2025: +3 units, 95% range −13 to +21). So: the ML forecast is modestly better; the ML warning system is not shown to be better than calibrated persistence. Intervals covered 79.5% in 2025 (winter 76%, up from 62% in my first version) but only 76% in Jan–Feb 2026 and 68% in Dec 2024. Failure: on 2025-05-21 the model forecast 46 and the reference was 152 µg/m³.

## What I'd do next
Validate against a real monitor (U.S. Consulate Lahore archive; tool ready, data not yet obtained), interview a school sports coordinator (plan in `STAKEHOLDER_REVIEW.md`, not yet done), and test the workflow on genuinely new days. No school has used this; no health benefit is claimed. This project is a prototype and is not medical advice.

## Sources
[Dataset](https://doi.org/10.5281/zenodo.18673725); [Open-Meteo/CAMS](https://open-meteo.com/en/docs/air-quality-api); [NumPy](https://numpy.org/), [pandas](https://pandas.pydata.org/), [Matplotlib](https://matplotlib.org/). **AI tools:** OpenAI ChatGPT/Codex and Anthropic Claude assisted with design, code, tests and writing; All reported results come from code run on the supplied dataset.
