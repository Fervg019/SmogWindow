"""Small, auditable NumPy models. No network, API key or scikit-learn required."""
import numpy as np
import pandas as pd

POLLUTANTS = ['pm10','carbon_monoxide','nitrogen_dioxide','sulphur_dioxide','ozone','aerosol_optical_depth','dust','uv_index']

def features(raw):
    d = raw.copy().sort_index()
    assert not d.index.duplicated().any(), 'Duplicate dates'
    d = d.reindex(pd.date_range(d.index.min(), d.index.max(), freq='D'))
    p = d.pm2_5
    x = pd.DataFrame(index=d.index)
    for lag in [0,1,2,3,6,13]:
        x[f'pm_lag_{lag}'] = p.shift(lag)
    for w in [3,7,14]:
        x[f'pm_mean_{w}'] = p.rolling(w, min_periods=w).mean()
        x[f'pm_std_{w}'] = p.rolling(w, min_periods=w).std()
    x['pm_change'] = p-p.shift(1)
    # Tomorrow's calendar is known at prediction time.
    day=(x.index+pd.Timedelta(days=1)).dayofyear
    for k in [1,2]:
        x[f'season_sin_{k}']=np.sin(2*np.pi*k*day/365.25)
        x[f'season_cos_{k}']=np.cos(2*np.pi*k*day/365.25)
    history=list(x.columns)
    for col in POLLUTANTS:
        x[col]=d[col]
        x[col+'_lag1']=d[col].shift(1)
    return x, p.shift(-1).rename('target'), history

def fit_model(x, y, config):
    a=np.asarray(x,float); y=np.asarray(y,float)
    mu=a.mean(axis=0); sd=a.std(axis=0); sd[sd<1e-9]=1
    z=(a-mu)/sd
    base=a[:,0]  # today's PM2.5
    residual=(np.log1p(y)-np.log1p(base)) if config.get('log') else y-base
    model={'config':config,'columns':list(x.columns),'mean':mu.tolist(),'scale':sd.tolist()}
    if config['kind']=='ridge':
        design=np.column_stack([np.ones(len(z)),z])
        penalty=np.eye(design.shape[1])*config['alpha']; penalty[0,0]=0
        beta=np.linalg.solve(design.T@design+penalty,design.T@residual)
        model['beta']=beta.tolist()
    else:
        # Gradient boosting of depth-one regression trees, fitted to change from persistence.
        # Quantile thresholds are computed only on fitting data.
        masks=[]; cuts=[]
        for j in range(z.shape[1]):
            for cut in np.unique(np.quantile(z[:,j],np.linspace(.1,.9,9))):
                mask=z[:,j]<=cut
                if min(mask.sum(),(~mask).sum())>=15:
                    masks.append(mask); cuts.append((j,float(cut)))
        masks=np.asarray(masks,float); counts=masks.sum(axis=1)
        init=float(residual.mean()); pred=np.full(len(y),init); trees=[]
        for _ in range(config['steps']):
            err=residual-pred; sums=masks@err
            left=sums/counts; right=(err.sum()-sums)/(len(y)-counts)
            gain=sums*sums/counts+(err.sum()-sums)**2/(len(y)-counts)
            ix=int(gain.argmax()); j,cut=cuts[ix]
            l=float(left[ix])*.05; r=float(right[ix])*.05
            pred+=np.where(z[:,j]<=cut,l,r)
            trees.append([j,cut,l,r])
        model.update(intercept=init,trees=trees)
    return model

def predict(model, x):
    a=np.asarray(x[model['columns']],float)
    z=(a-np.array(model['mean']))/np.array(model['scale'])
    if model['config']['kind']=='ridge':
        delta=np.column_stack([np.ones(len(z)),z])@np.array(model['beta'])
    else:
        delta=np.full(len(z),model['intercept'])
        for j,cut,l,r in model['trees']:
            delta+=np.where(z[:,j]<=cut,l,r)
    if model['config'].get('log'):
        return np.maximum(0,np.expm1(np.log1p(a[:,0])+delta))
    return np.maximum(0,a[:,0]+delta)

def warning_metrics(y, score, threshold=55., ratio=3.):
    actual=np.asarray(y)>threshold; flag=np.asarray(score)>threshold
    tp=int((actual&flag).sum()); fn=int((actual&~flag).sum())
    fp=int((~actual&flag).sum()); tn=int((~actual&~flag).sum())
    return dict(tp=tp,fn=fn,fp=fp,tn=tn,recall=tp/(tp+fn) if tp+fn else None,
                precision=tp/(tp+fp) if tp+fp else None,flagged=int(flag.sum()),
                cost=float(ratio*fn+fp),threshold=float(threshold),ratio=float(ratio))


# ---------------------------------------------------------------- v2 additions
MINIMAL=['pm_lag_0','pm_mean_7','pm_change','season_sin_1','season_cos_1']

def columns_for(config, all_columns, history):
    """Feature columns a candidate may use: 'history' (PM2.5+calendar), 'minimal', or 'full'."""
    return {'history':list(history),'minimal':[c for c in MINIMAL if c in all_columns],'full':list(all_columns)}[config['features']]

def climatology(train_target_dates, train_y, query_dates, half_window=15):
    """Mean of training-period targets within +-half_window calendar days of each query date."""
    td=np.asarray(pd.DatetimeIndex(train_target_dates).dayofyear); ty=np.asarray(train_y,float)
    out=[]
    for q in pd.DatetimeIndex(query_dates).dayofyear:
        gap=np.abs(td-q); gap=np.minimum(gap,365-gap)
        m=gap<=half_window
        out.append(ty[m].mean() if m.any() else ty.mean())
    return np.array(out)

def data_quality(raw, origin, lookback=14):
    """Plain-language warnings for the 14-day window that feeds a forecast issued on `origin`.
    `raw` is a daily DataFrame indexed by date with a pm2_5 column."""
    origin=pd.Timestamp(origin)
    window=raw.reindex(pd.date_range(origin-pd.Timedelta(days=lookback-1),origin,freq='D')).pm2_5
    flags=[]
    missing=int(window.isna().sum())
    if missing: flags.append(f'{missing} of the last {lookback} days have no PM2.5 value; a forecast cannot be issued until the gap is filled.')
    if raw.index.max()<origin: flags.append('No data on or after the origin date; the forecast would be an extrapolation.')
    if window.notna().all() and window.iloc[-1]>raw.pm2_5.quantile(.99):
        flags.append('Today is above the 99th percentile of all history; forecasts for extreme days are least reliable.')
    return {'missing_days':missing,'complete':missing==0,'flags':flags}
