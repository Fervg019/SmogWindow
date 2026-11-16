"""Fetch recent daily values in the same format as data/air_quality_historical.csv (UNTESTED against the live API:
the build environment had no network access; the parsing is unit-tested on a mock response in test_integrity.py).

    python fetch_open_meteo.py --days 30 --out recent.csv
    # then append the new dates to the packaged CSV (keep the header) and run plan_live.py --data merged.csv

Open-Meteo returns hourly CAMS values; we average them per calendar day in the requested timezone. The packaged
dataset does not say which timezone its daily means used, so a seam between old and new rows is possible."""
import argparse, json, urllib.request
import pandas as pd

VARS = ['pm10', 'pm2_5', 'carbon_monoxide', 'nitrogen_dioxide', 'sulphur_dioxide', 'ozone', 'aerosol_optical_depth', 'dust', 'uv_index']
URL = ('https://air-quality-api.open-meteo.com/v1/air-quality?latitude=31.558&longitude=74.35071&hourly=' + ','.join(VARS) +
       '&past_days={days}&forecast_days=0&timezone={tz}')


def hourly_to_daily(payload, min_hours=20):
    h = pd.DataFrame(payload['hourly']); h['time'] = pd.to_datetime(h['time']); h = h.set_index('time')
    days = h.groupby(h.index.date)
    daily = days[VARS].mean(); daily['hours'] = days['pm2_5'].count()
    daily = daily[daily.hours >= min_hours].drop(columns='hours')          # drop partial days instead of averaging them
    daily.index = pd.to_datetime(daily.index); daily.index.name = 'date'
    return daily.round(4)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=30); ap.add_argument('--tz', default='UTC'); ap.add_argument('--out', default='recent.csv')
    a = ap.parse_args()
    with urllib.request.urlopen(URL.format(days=min(a.days, 92), tz=a.tz), timeout=30) as r:
        daily = hourly_to_daily(json.load(r))
    daily.to_csv(a.out); print(f'wrote {len(daily)} complete days to {a.out}')
