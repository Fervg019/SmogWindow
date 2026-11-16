"""Past-only rolling interval calibration. Post-benchmark research, not a fresh test."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent;R=P/"research_results"
def calibrate(df,window):
 d=df.sort_values("target_date").copy();score=np.maximum(d.q10-d.actual,d.actual-d.q90).to_numpy();lo=[];hi=[]
 for i in range(len(d)):
  # At end of origin day, earlier target outcomes are available; current target excluded.
  hist=score[max(0,i-window):i]
  if len(hist)<30:lo.append(np.nan);hi.append(np.nan);continue
  rank=min(len(hist),int(np.ceil((len(hist)+1)*.8)));adj=max(0,float(np.sort(hist)[rank-1]))
  lo.append(max(0,float(d.q10.iloc[i])-adj));hi.append(float(d.q90.iloc[i])+adj)
 d["cal_low"]=lo;d["cal_high"]=hi
 d["cal_covered"]=(d.actual>=d.cal_low)&(d.actual<=d.cal_high)
 d["cal_width"]=d.cal_high-d.cal_low
 d["cal_score"]=d.cal_width+10*np.maximum(d.cal_low-d.actual,0)+10*np.maximum(d.actual-d.cal_high,0)
 return d

def main():
 lock=json.loads((R/"weather_selection_frozen.json").read_text());raw=pd.read_csv(R/"all_probability_predictions.csv");d=raw[raw.model==lock["probabilistic_model"]].copy()
 dev={}
 for w in [60,90,180]:
  c=calibrate(d[d.target_date<"2025-01-01"],w);z=c[c.target_date>="2023-09-01"].dropna(subset=["cal_score"])
  dev[w]={"interval_score":float(z.cal_score.mean()),"coverage":float(z.cal_covered.mean()),"width":float(z.cal_width.mean())}
 selected=min(dev,key=lambda w:dev[w]["interval_score"])
 c=calibrate(d,selected);out={"window":selected,"selection":"development interval score only; entire experiment designed after benchmark inspection","development":dev,"periods":{}}
 for name,lo,hi in [("2025","2025-01-01","2025-12-31"),("January2026","2026-01-01","2026-01-31")]:
  z=c[c.target_date.between(lo,hi)];out["periods"][name]={"n":len(z),"original_coverage":float(z.covered.mean()),"calibrated_coverage":float(z.cal_covered.mean()),"original_width":float(z.width.mean()),"calibrated_width":float(z.cal_width.mean()),"original_interval_score":float(z.interval_score.mean()),"calibrated_interval_score":float(z.cal_score.mean())}
 # Mutation test: changing current and later outcomes cannot affect earlier/current bounds.
 altered=d.copy();cut=len(d)-20;altered.iloc[cut:,altered.columns.get_loc("actual")]+=1000
 check=calibrate(altered,selected);assert np.allclose(c.cal_low.iloc[:cut+1],check.cal_low.iloc[:cut+1],equal_nan=True);assert np.allclose(c.cal_high.iloc[:cut+1],check.cal_high.iloc[:cut+1],equal_nan=True)
 (R/"interval_calibration.json").write_text(json.dumps(out,indent=2));c.to_csv(R/"calibrated_intervals.csv",index=False)
 rows=pd.read_csv(R/"dashboard_rows.csv");rows=rows.drop(columns=[x for x in ["cal_low","cal_high"] if x in rows]);rows=rows.merge(c[["target_date","cal_low","cal_high"]],on="target_date",validate="one_to_one");rows.to_csv(R/"dashboard_rows.csv",index=False)
 print(json.dumps(out,indent=2));print("PASS: current/future outcome mutation cannot change available interval")
if __name__=="__main__":main()
