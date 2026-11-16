"""Conditional empirical distributions and proper scores; no post-hoc error margin."""
import numpy as np

def distribution_samples(train_x,train_y,query_x,kind='analog',k=60):
    tx=np.asarray(train_x,float);qx=np.asarray(query_x,float);y=np.asarray(train_y,float)
    changes=y-tx[:,0]
    if kind=='trailing':tx=tx[-180:];changes=changes[-180:]
    mu=tx.mean(axis=0);sd=tx.std(axis=0);sd[sd<1e-9]=1
    z=(tx-mu)/sd
    for row in qx:
        if kind=='analog':
            dist=np.sqrt(((z-(row-mu)/sd)**2).sum(axis=1));ix=np.argsort(dist,kind='stable')[:min(k,len(tx))]
            w=1/(dist[ix]+.1);v=np.maximum(0,row[0]+changes[ix])
        else:w=np.ones(len(changes));v=np.maximum(0,row[0]+changes)
        order=np.argsort(v,kind='stable');yield v[order],(w/w.sum())[order]

def distribution_summary(values,weights,actual):
    v=np.asarray(values,float);w=np.asarray(weights,float);cum=np.cumsum(w)
    def quant(q):return float(v[min(np.searchsorted(cum,q,side='left'),len(v)-1)])
    q10,q50,q90=[quant(q) for q in [.1,.5,.9]]
    # Exact CRPS for a weighted discrete predictive distribution.
    half_pair=float(np.sum(w*v*(2*(cum-w)+w-1)))
    crps=float(np.sum(w*abs(v-actual))-half_pair)
    result={'q10':q10,'q50':q50,'q90':q90,'mean':float(w@v),'crps':crps,'width':q90-q10,
      'covered':int(q10<=actual<=q90),'interval_score':q90-q10+10*max(q10-actual,0)+10*max(actual-q90,0)}
    for q,est in [(.1,q10),(.5,q50),(.9,q90)]:result[f'pinball_{q}']=float(max(q*(actual-est),(q-1)*(actual-est)))
    for t in [35,55,100]:
        p=float(np.clip(w[v>t].sum(),0,1));result[f'p_gt_{t}']=p;result[f'brier_{t}']=(p-float(actual>t))**2
    return result
