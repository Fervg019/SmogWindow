"""Validate uploaded Open-Meteo hourly export and create conservative past-weather inputs."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

def read_weather(path):
    path=Path(path)
    meta=pd.read_csv(path,nrows=1).iloc[0].to_dict()
    if int(meta['utc_offset_seconds'])!=0:raise ValueError('Expected UTC export; do not silently reinterpret another timezone')
    raw=pd.read_csv(path,skiprows=3)
    raw.columns=[c.split(' (')[0] for c in raw.columns]
    raw['time']=pd.to_datetime(raw.time,errors='raise')
    if raw.time.duplicated().any():raise ValueError('Duplicate weather timestamps; unique hours required')
    raw=raw.set_index('time').sort_index()
    needed=['temperature_2m','relative_humidity_2m','precipitation','wind_speed_10m','wind_direction_10m','surface_pressure']
    if not np.isfinite(raw[needed].to_numpy()).all():raise ValueError('Nonfinite weather values; inspect before averaging')
    if (raw.precipitation<0).any() or (raw.wind_speed_10m<0).any():raise ValueError('Invalid negative rain or wind')
    if not raw.relative_humidity_2m.between(0,100).all():raise ValueError('Humidity out of range')
    if not raw.wind_direction_10m.between(0,360).all():raise ValueError('Wind direction out of range')
    raw['u']=-raw.wind_speed_10m*np.sin(np.deg2rad(raw.wind_direction_10m))
    raw['v']=-raw.wind_speed_10m*np.cos(np.deg2rad(raw.wind_direction_10m))
    g=raw.resample('D');counts=g[needed].count()
    daily=pd.DataFrame({'wx_temperature_mean':g.temperature_2m.mean(),'wx_temperature_range':g.temperature_2m.max()-g.temperature_2m.min(),
       'wx_humidity_mean':g.relative_humidity_2m.mean(),'wx_humidity_max':g.relative_humidity_2m.max(),
       'wx_rain_sum':g.precipitation.sum(min_count=24),'wx_wind_mean':g.wind_speed_10m.mean(),
       'wx_wind_min':g.wind_speed_10m.min(),'wx_wind_max':g.wind_speed_10m.max(),
       'wx_wind_u':g.u.mean(),'wx_wind_v':g.v.mean(),'wx_pressure_mean':g.surface_pressure.mean()})
    complete=(counts==24).all(axis=1);daily.loc[~complete,:]=np.nan
    daily['wx_pressure_change']=daily.wx_pressure_mean.diff()
    audit={'source_file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'metadata':meta,'hourly_rows':len(raw),
       'first_hour':str(raw.index.min()),'last_hour':str(raw.index.max()),'complete_days':int(complete.sum()),'incomplete_days':int((~complete).sum()),
       'forecast_issue_time_available':False,'weather_product':'not specified by supplied export','timing':'one UTC day lag before origin-date inputs',
       'coordinates_note':'Weather grid coordinates differ from pollution city coordinates; both represent gridded model products, not school measurements.'}
    return daily,audit

def attach_weather(x,daily):
    # Shift on a full daily calendar before reindexing: a missing date cannot become yesterday.
    d=daily.reindex(pd.date_range(daily.index.min(),daily.index.max(),freq='D'))
    lag=d.shift(1).reindex(x.index)
    return x.join(lag),list(lag.columns)
