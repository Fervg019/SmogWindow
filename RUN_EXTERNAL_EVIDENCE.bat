@echo off
cd /d "%~dp0"
python fetch_monitor_archive.py
if errorlevel 1 goto monitorfailed
python validate_research_ground.py --ground data/monitor/ground_daily_utc.csv --out research_results/ground_utc.json
python validate_research_ground.py --ground data/monitor/ground_daily_local.csv --out research_results/ground_local.json
:monitorfailed
python fetch_karachi.py
if errorlevel 1 goto end
python test_frozen_transfer.py --city-csv data/karachi/air_quality_historical.csv --city Karachi
:end
echo Review errors above. Failed downloads are NOT successful validations.
pause
