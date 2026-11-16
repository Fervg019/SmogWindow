"""Run weather/probability development then locked benchmark reporting.
python weather_research.py --stage develop
python weather_research.py --stage evaluate
"""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd
from model import features,fit_model,predict
from evaluation import load_series,block_bootstrap
from weather_features import read_weather,attach_weather
from probability_models import distribution_samples,distribution_summary
P=Path(__file__).resolve().parent;R=P/'research_results';R.mkdir(exist_ok=True)
ANALOG=['pm_lag_0','pm_lag_1','pm_mean_7','pm_change','season_sin_1','season_cos_1']
BLOCKS=[('2023 Sep-Nov','2023-09-01','2023-11-30'),('2023 Dec-Feb','2023-12-01','2024-02-29'),('2024 Mar-May','2024-03-01','2024-05-31'),('2024 Jun-Aug','2024-06-01','2024-08-31'),('2024 Sep-Nov','2024-09-01','2024-11-30'),('2024 Dec','2024-12-01','2024-12-31')]
def dump(name,v):(R/name).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def frame():
    raw=load_series(P/'data/air_quality_historical.csv');x,y,h=features(raw);base=list(x.columns)
    daily,audit=read_weather(P/'data/weather_hourly_utc.csv');x,wx=attach_weather(x,daily)
    ok=x.notna().all(axis=1)&y.notna();x=x[ok];y=y[ok]
    return x,y,x.index+pd.Timedelta(days=1),base,wx,audit
def specs():
    return [{'name':f'Analog {group} k{k}','kind':'analog','weather':group=='weather','k':k} for group in ['history','weather'] for k in [30,60,120]]+[
      {'name':'Persistence empirical expanding','kind':'expanding','weather':False,'k':0},
      {'name':'Persistence empirical trailing180','kind':'trailing','weather':False,'k':0}]
def forecasts(last,selected_prob=None):
    x,y,dates,base,wx,audit=frame();keep=dates<=pd.Timestamp(last);x=x[keep];y=y[keep];dates=dates[keep]
    sel=np.flatnonzero(dates>='2023-03-01');months=pd.PeriodIndex(dates[sel],freq='M');rows=[];prows=[]
    candidates=specs() if selected_prob is None else [s for s in specs() if s['name'] in selected_prob]
    for month in months.unique():
        te=sel[np.asarray(months==month)];tr=np.flatnonzero(dates<month.start_time)
        assert len(tr)>=120 and dates[tr].max()<dates[te].min()
        point={}
        for group,cols in [('no_weather',base),('weather',base+wx)]:
            for alpha in [100,1000]:
                cfg={'kind':'ridge','alpha':alpha,'features':group};m=fit_model(x.iloc[tr][cols],y.iloc[tr],cfg)
                point[f'Ridge {group} a{alpha}']=predict(m,x.iloc[te])
        for j,i in enumerate(te):
            rows.append({'origin_date':str(x.index[i].date()),'target_date':str(dates[i].date()),'actual':float(y.iloc[i]),'Persistence':float(x.pm_lag_0.iloc[i]),
              'pm_change':float(x.pm_change.iloc[i]),'lagged_rain':float(x.wx_rain_sum.iloc[i]),'lagged_wind':float(x.wx_wind_mean.iloc[i]),**{n:float(p[j]) for n,p in point.items()}})
        for spec in candidates:
            cols=ANALOG+(wx if spec['weather'] else [])
            samples=distribution_samples(x.iloc[tr][cols],y.iloc[tr],x.iloc[te][cols],spec['kind'],spec['k'])
            for i,(values,weights) in zip(te,samples):
                prows.append({'model':spec['name'],'target_date':str(dates[i].date()),'actual':float(y.iloc[i]),**distribution_summary(values,weights,float(y.iloc[i]))})
    return pd.DataFrame(rows),pd.DataFrame(prows),audit
def probmetrics(df):
    cols=['crps','width','covered','interval_score','pinball_0.1','pinball_0.5','pinball_0.9','brier_35','brier_55','brier_100']
    out={c:float(df[c].mean()) for c in cols};out.update(n=len(df),median_mae=float(np.mean(abs(df.actual-df.q50))))
    return out
def develop():
    f,p,a=forecasts('2024-12-31');f.to_csv(R/'development_points.csv',index=False);p.to_csv(R/'development_probabilities.csv',index=False);dump('weather_audit.json',a)
    dev=f.target_date>='2023-09-01';pdv=p[p.target_date>='2023-09-01']
    pointcols=[c for c in f if c.startswith('Ridge')]+['Persistence']
    rankings={c:float(np.mean(abs(f.loc[dev,'actual']-f.loc[dev,c]))) for c in pointcols}
    prob={n:probmetrics(df) for n,df in pdv.groupby('model')}
    learned=[s['name'] for s in specs() if s['kind']=='analog'];baselines=[s['name'] for s in specs() if s['kind']!='analog']
    best=min(learned,key=lambda n:prob[n]['crps']);bestbase=min(baselines,key=lambda n:prob[n]['crps'])
    bestweather=min([c for c in rankings if c.startswith('Ridge weather')],key=rankings.get)
    besthistory=min([c for c in rankings if c.startswith('Ridge no_weather')],key=rankings.get)
    pre=f[f.target_date<'2023-09-01']
    lock={'point_weather':bestweather,'point_no_weather':besthistory,'probabilistic_model':best,'probabilistic_baseline':bestbase,
      'point_development_mae':rankings,'probability_development':prob,'group_thresholds':{'abrupt_abs_change':float(abs(pre.pm_change).quantile(.9)),'stagnant_wind':float(pre.lagged_wind.quantile(.25)),'realized_spike':float(pre.actual.quantile(.9))},
      'selection_period':'2023-09-01 to 2024-12-31 only','all_later_periods':'already inspected benchmarks, not fresh holdouts','protocol_sha256':hashlib.sha256((P/'WEATHER_PROTOCOL.json').read_bytes()).hexdigest()}
    dump('weather_selection_frozen.json',lock)
    block=[]
    for label,start,end in BLOCKS:
        sub=f[f.target_date.between(start,end)]
        for c in pointcols:block.append({'block':label,'kind':'point','model':c,'n':len(sub),'score':float(np.mean(abs(sub.actual-sub[c]))),'score_name':'MAE'})
        for n,subp in pdv[pdv.target_date.between(start,end)].groupby('model'):block.append({'block':label,'kind':'probability','model':n,'n':len(subp),'score':float(subp.crps.mean()),'score_name':'CRPS'})
    pd.DataFrame(block).to_csv(R/'development_blocks.csv',index=False)
    print(json.dumps({'point_mae':rankings,'probability_crps':{n:v['crps'] for n,v in prob.items()},'selected':[bestweather,besthistory,best,bestbase]},indent=2))
def evaluate():
    lock=json.loads((R/'weather_selection_frozen.json').read_text());assert lock['protocol_sha256']==hashlib.sha256((P/'WEATHER_PROTOCOL.json').read_bytes()).hexdigest()
    # Include matched weather/no-weather probabilistic pairs to show the whole weather ablation.
    f,p,a=forecasts('2026-01-31');f.to_csv(R/'all_point_predictions.csv',index=False);p.to_csv(R/'all_probability_predictions.csv',index=False)
    result={'selection':lock,'periods':{}};reliability=[];subgroups=[];warnings=[]
    for label,lo,hi in [('known_2025','2025-01-01','2025-12-31'),('known_Jan2026','2026-01-01','2026-01-31')]:
        sub=f[f.target_date.between(lo,hi)].copy();px=p[p.target_date.between(lo,hi)];y=sub.actual.to_numpy()
        pointcols=[c for c in f if c.startswith('Ridge')]+['Persistence']
        scores={n:{'mae':float(np.mean(abs(y-sub[n]))),'rmse':float(np.sqrt(np.mean((y-sub[n])**2)))} for n in pointcols}
        comparisons={}
        for n,baseline in [(lock['point_weather'],lock['point_no_weather']),(lock['point_weather'],'Persistence')]:
            delta=abs(y-sub[baseline].to_numpy())-abs(y-sub[n].to_numpy())
            comparisons[f'{n} vs {baseline}']={'mae_reduction':float(delta.mean()),'ci95_by_block':{str(b):block_bootstrap(delta,block=b,n=2000) for b in [3,7,14]}}
        probs={n:probmetrics(df) for n,df in px.groupby('model')}
        chosen=px[px.model==lock['probabilistic_model']].sort_values('target_date');base=px[px.model==lock['probabilistic_baseline']].sort_values('target_date')
        delta=base.crps.to_numpy()-chosen.crps.to_numpy()
        result['periods'][label]={'n':len(sub),'point':scores,'point_comparisons':comparisons,'probability':probs,'crps_advantage':float(delta.mean()),'crps_advantage_ci95':block_bootstrap(delta)}
        for n,df in [(lock['probabilistic_model'],chosen),(lock['probabilistic_baseline'],base)]:
            for threshold in [35,55,100]:
                pr=df[f'p_gt_{threshold}'].to_numpy();truth=(df.actual.to_numpy()>threshold).astype(float)
                for b in range(5):
                    mask=(pr>=b*.2)&((pr<(b+1)*.2) if b<4 else (pr<=1));count=int(mask.sum())
                    reliability.append({'period':label,'model':n,'threshold':threshold,'bin_low':b*.2,'bin_high':(b+1)*.2,'n':count,'mean_probability':float(pr[mask].mean()) if count else None,'observed_frequency':float(truth[mask].mean()) if count else None})
                for cost in [1,3,5]:
                    flag=pr>1/(1+cost);positive=truth.astype(bool);fn=int((positive&~flag).sum());fp=int((~positive&flag).sum())
                    warnings.append({'period':label,'model':n,'threshold':threshold,'ratio':cost,'n':len(df),'high_days':int(positive.sum()),'missed':fn,'false_alarms':fp,'flagged':int(flag.sum()),'cost':cost*fn+fp,'always_flag_cost':int((~positive).sum()),'never_flag_cost':cost*int(positive.sum())})
        t=lock['group_thresholds'];dt=pd.to_datetime(sub.target_date)
        masks={'Winter':dt.dt.month.isin([12,1,2]),'Nonwinter':~dt.dt.month.isin([12,1,2]),'Prior abrupt change':abs(sub.pm_change)>t['abrupt_abs_change'],'No prior abrupt change':abs(sub.pm_change)<=t['abrupt_abs_change'],'Lagged rain':sub.lagged_rain>0,'No lagged rain':sub.lagged_rain==0,'Stagnant prior wind':sub.lagged_wind<t['stagnant_wind'],'Other prior wind':sub.lagged_wind>=t['stagnant_wind'],'Realized spike (retrospective)':sub.actual>t['realized_spike'],'Other realized days':sub.actual<=t['realized_spike']}
        for group,mask in masks.items():
            g=sub.loc[mask]
            if len(g)==0:continue
            for n in [lock['point_weather'],lock['point_no_weather'],'Persistence']:
                subgroups.append({'period':label,'group':group,'model':n,'n':len(g),'mae':float(np.mean(abs(g.actual-g[n]))),'rmse':float(np.sqrt(np.mean((g.actual-g[n])**2)))})
    dump('weather_metrics.json',result);pd.DataFrame(reliability).to_csv(R/'reliability.csv',index=False);pd.DataFrame(warnings).to_csv(R/'probability_warning_sensitivity.csv',index=False);pd.DataFrame(subgroups).to_csv(R/'conditional_performance.csv',index=False)
    chosen=p[p.model==lock['probabilistic_model']].copy();chosen=chosen[chosen.target_date>='2025-01-01'].merge(f[['target_date','origin_date','actual',lock['point_weather'],lock['point_no_weather'],'Persistence','lagged_wind','lagged_rain']],on=['target_date','actual'])
    chosen.to_csv(R/'dashboard_rows.csv',index=False)
    print(json.dumps({'selected':{k:v for k,v in lock.items() if k in ['point_weather','point_no_weather','probabilistic_model','probabilistic_baseline']},'periods':{k:{'n':v['n'],'point':v['point'],'probabilistic_selected':v['probability'][lock['probabilistic_model']],'probabilistic_baseline':v['probability'][lock['probabilistic_baseline']],'crps_advantage_ci95':v['crps_advantage_ci95']} for k,v in result['periods'].items()}},indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['develop','evaluate'],default='develop');args=ap.parse_args()
    {'develop':develop,'evaluate':evaluate}[args.stage]()
