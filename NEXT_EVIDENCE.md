# Remaining evidence: implementation and honest status

## Implemented now

- Public OpenAQ station 8664 downloader with resumable daily files, station/sensor/unit checks and both UTC/local daily aggregation. No API key is needed for the documented public archive route. Archive availability is not established until the download succeeds.
- Ground scoring for all four new ridge variants, CAMS persistence and actual monitor persistence on identical dates. Reports CAMS-versus-monitor bias separately, by year, without choosing a favorable timezone shift.
- CAMS comparator input validation: explicit issue, availability and decision timestamps; no forecasts available after the decision; no repeated target dates or implicit units. Input must be a verified daily aggregate on the same daily boundary. This is not a raw GRIB converter.
- Karachi downloader with published checksum verification, and a Lahore-only frozen-coefficient transfer test. Destination data are never used to fit or tune the model.
- A blank stakeholder evidence form. No interviews or numerical preferences have been invented.

## Execution status

Local network requests fail with DNS resolution errors. The search service could read source documentation but could not return the binary archive files. Therefore no new ground, CAMS or transfer scores exist. Run RUN_EXTERNAL_EVIDENCE.bat on a connected computer to attempt monitor and Karachi acquisition and evaluation. It reports failures rather than substituting synthetic data. Dependencies remain those in requirements.txt.

For a normalized issued CAMS daily CSV:
`python compare_issued_forecasts.py your_issued_cams.csv`
Required schema and cutoff rules are in the script. Download original forecasts through the Copernicus Atmosphere Data Store; account access and verified issue-time aggregation are still required. The comparator currently scores the bundled CAMS-series target, so it cannot establish independent real-world superiority.

A real teacher or sports coordinator must provide the stakeholder answers. Their role/date, consent, existing process and verbatim feedback belong in STAKEHOLDER_RESPONSE_TEMPLATE.json. Do not convert a blank form into a claimed pilot. Competition submission/extension status also remains unconfirmed.

## Findings that remain limitations

The small weather gain, January probability undercoverage, previously inspected benchmark periods and modeled targets cannot be fixed by changing report wording. The dashboard still displays these limitations. No thresholds were retuned on January to make its results look better. A fresh prospective or independent evaluation is required for stronger claims.

## Verified source leads (16 November 2026)

- Station identity: https://explore.openaq.org/locations/8664
- Archive schema: https://docs.openaq.org/aws/about
- Public archive access: https://registry.opendata.aws/openaq/
- Karachi source: https://zenodo.org/records/18673762 (modeled CAMS data, not measurements)
- CAMS issued forecasts: https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts
- Weather archive distinction: https://open-meteo.com/en/docs/historical-forecast-api

Open-Meteo's historical forecast series stitches early forecast hours; its Previous Runs API is weather-specific and does not by itself establish archived issued CAMS PM2.5 availability. Do not label the existing weather export day-ahead weather.
