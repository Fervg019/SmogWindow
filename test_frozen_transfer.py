"""Frozen Lahore coefficients, no destination fitting. Destination uses same CSV schema."""
import argparse,json,hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from evaluation import load_series
from model import features,fit_model,predict
P=Path(__file__).resolve().parent
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--city-csv",required=True);a.add_argument("--city",required=True);v=a.parse_args()
 x,y,_=features(load_series(P/"data/air_quality_historical.csv"));mask=x.notna().all(axis=1)&y.notna()&((x.index+pd.Timedelta(days=1))<"2025-01-01")
 m=fit_model(x[mask],y[mask],{"kind":"ridge","alpha":1000});frozen=json.dumps(m,sort_keys=True);(P/"research_results/frozen_lahore_transfer_model.json").write_text(frozen)
 dx,dy,_=features(load_series(v.city_csv));dates=dx.index+pd.Timedelta(days=1);ok=dx.notna().all(axis=1)&dy.notna()&(dates>="2025-01-01")&(dates<="2026-01-31")
 dx=dx[ok];dy=dy[ok]
 if len(dy)<60:raise ValueError("Fewer than 60 comparable destination days")
 pred=predict(m,dx);rows=pd.DataFrame({"target_date":dates[ok],"actual":dy.values,"frozen_lahore":pred,"destination_persistence":dx.pm_lag_0.values})
 r={"city":v.city,"n":len(rows),"training":"Lahore targets before 2025 only; alpha from existing development selection","model_sha256":hashlib.sha256(frozen.encode()).hexdigest(),"mae":float(abs(pred-dy).mean()),"persistence_mae":float(abs(dx.pm_lag_0-dy).mean()),"limits":"Same-source modeled-series transfer; no destination refit or independent monitor validation"}
 (P/"research_results/transfer.json").write_text(json.dumps(r,indent=2));rows.to_csv(P/"research_results/transfer_predictions.csv",index=False);print(json.dumps(r,indent=2))
