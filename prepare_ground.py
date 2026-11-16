"""Prepare real monitor hours without silently mixing local and UTC days.
Example: python prepare_ground.py input.csv --time-col timestamp --value-col pm25
         --input-timezone Asia/Karachi --daily-timezone UTC --out ground_daily.csv
No ground measurements are bundled. Do not use AQI or NowCast as hourly concentration.
"""
import argparse
import pandas as pd

def prepare(df,time_col,value_col,input_timezone,daily_timezone,min_hours=18):
    t=pd.to_datetime(df[time_col],errors='coerce');v=pd.to_numeric(df[value_col],errors='coerce')
    if t.dt.tz is None:t=t.dt.tz_localize(input_timezone,ambiguous='NaT',nonexistent='NaT')
    t=t.dt.tz_convert(daily_timezone)
    good=t.notna()&v.notna()&(v>=0)
    s=pd.Series(v[good].to_numpy(),index=pd.DatetimeIndex(t[good])).sort_index()
    if s.index.floor('h').duplicated().any():raise ValueError('Duplicate hours: resolve repeated readings or station mixing before daily averaging')
    g=s.resample('D');out=pd.DataFrame({'pm2_5':g.mean(),'valid_hours':g.count()});out=out[out.valid_hours>=min_hours]
    out.index=out.index.tz_localize(None);out.index.name='date'
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('csv');p.add_argument('--time-col',required=True);p.add_argument('--value-col',required=True);p.add_argument('--input-timezone',required=True);p.add_argument('--daily-timezone',required=True);p.add_argument('--min-hours',type=int,default=18);p.add_argument('--out',required=True);a=p.parse_args()
    df=prepare(pd.read_csv(a.csv),a.time_col,a.value_col,a.input_timezone,a.daily_timezone,a.min_hours);df.to_csv(a.out)
    print(f'{len(df)} daily values saved. Apply source quality flags before running; CAMS daily timezone remains undocumented and must be resolved before a definitive ground comparison.')
