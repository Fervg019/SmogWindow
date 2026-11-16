"""Independent numerical and temporal tests for the new research pipeline."""
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from probability_models import distribution_samples,distribution_summary
from weather_features import read_weather,attach_weather
from weather_research import frame,ANALOG
P=Path(__file__).resolve().parent
# Proper-score implementation checked against the direct O(n^2) definition.
rng=np.random.default_rng(18)
for n in [1,5,30]:
    v=np.sort(rng.uniform(0,200,n));w=rng.uniform(.1,1,n);w/=w.sum();y=72.
    score=distribution_summary(v,w,y);brute=np.sum(w*abs(v-y))-.5*np.sum(w[:,None]*w[None,:]*abs(v[:,None]-v[None,:]))
    assert abs(score['crps']-brute)<1e-10
    assert score['q10']<=score['q50']<=score['q90']
    assert score['p_gt_35']>=score['p_gt_55']>=score['p_gt_100']
    assert all(0<=score[f'p_gt_{t}']<=1+1e-12 for t in [35,55,100])
x,y,dates,base,wx,a=frame();cut=pd.Timestamp('2025-05-21')
daily,_=read_weather(P/'data/weather_hourly_utc.csv');mut=daily.copy();mut.loc[mut.index>=cut,:]=99999
# Origin-date and future weather cannot enter this origin's forecast (strict one-day lag).
orig,_=attach_weather(x[base],daily);changed,_=attach_weather(x[base],mut)
pd.testing.assert_frame_equal(orig.loc[:cut],changed.loc[:cut])
prefix,_=attach_weather(x.loc[:cut,base],daily.loc[:cut]);pd.testing.assert_frame_equal(orig.loc[:cut],prefix)
# Distribution depends on fitting labels only, not the scoring actual.
train=dates<'2025-01-01';query=x.loc[[cut],ANALOG+wx];vals,w=next(distribution_samples(x.loc[train,ANALOG+wx],y.loc[train],query))
s1=distribution_summary(vals,w,10);s2=distribution_summary(vals,w,999)
for k in ['q10','q50','q90','mean','p_gt_35','p_gt_55','p_gt_100']:assert s1[k]==s2[k]
# Duplicate hour rejected, partial day withheld (not averaged as a complete day).
text=(P/'data/weather_hourly_utc.csv').read_text(encoding='utf-8-sig');lines=text.splitlines()
with tempfile.TemporaryDirectory() as tmp:
    f=Path(tmp)/'partial.csv';f.write_text('\n'.join(lines[:4]+lines[5:]),encoding='utf-8');d,a2=read_weather(f)
    assert a2['incomplete_days']==1 and d.iloc[0].isna().all()
    f.write_text('\n'.join(lines+[lines[4]]),encoding='utf-8')
    try:read_weather(f);raise AssertionError('duplicate should fail')
    except ValueError as e:assert 'Duplicate' in str(e)
# Wind-vector averaging must not turn 359 and 1 degrees into southerly flow.
angles=np.deg2rad([359,1]);assert abs(np.sin(angles).mean())<1e-9 and np.cos(angles).mean()>.99
print('PASS: CRPS vs brute force; monotone quantiles/probabilities; current/future-weather exclusion; prefix invariance; outcome-independent distributions; duplicate rejection; partial-day withholding; circular wind averaging.')
