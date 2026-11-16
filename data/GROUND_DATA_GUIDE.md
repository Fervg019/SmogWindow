# Getting ground-monitor data (not bundled; none was obtained for this version)

**Status: no independent ground data have been validated against this project.** Every result in the write-up uses CAMS modeled PM2.5. The tooling to test against a real monitor is ready; the data are not.

## Candidate source (verify before use)
- **U.S. Consulate Lahore reference monitor** via AirNow's embassy/consulate archive (EPA/State Department): the AirNow "Embassies and Consulates" map has an Archive tab / "Historical" links that provide downloadable hourly PM2.5 files. Data there are described as preliminary and subject to later QA. Check the file's own header, units, timezone (local time) and licence yourself; do not assume the column names below.
- Other candidates (check coverage and provenance first): OpenAQ station records for Lahore, Punjab Environmental Protection Department monitors (reported to be offline often and inconsistent with other sources), PAQI community sensors.
- The monitor is at one location in Lahore. It is NOT a school site, and the CAMS grid cell is ~0.4 degrees wide.

## How to use it
```
python validate_ground.py --ground <file>.csv --hourly --time-col "<time column>" --value-col "<PM2.5 column>"
```
The script averages hours to days (>=18 valid hours), refuses fewer than 60 overlapping days, checks day alignment (timezone seams), reports CAMS-versus-monitor bias/correlation, and re-scores the walk-forward forecasts against the monitor's next-day values, including a monitor-only persistence baseline. Write the actual numbers into the write-up only after you run it on a real file. If the best alignment is not shift 0, resolve the timezone issue first.
