"""Score all saved point forecasts against explicitly aligned real measurements."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parent

def validate(path):
 g=pd.read_csv(path,parse_dates=["date"]).set_index("date").pm2_5
 if g.index.duplicated().any() or not np.isfinite(g).all() or (g<0).any():raise ValueError("Invalid daily monitor values")
 f=pd.read_csv(P/"research_results/all_point_predictions.csv",parse_dates=["target_date","origin_date"])
 f["ground"]=f.target_date.map(g);f["Ground persistence"]=f.origin_date.map(g)
 cols=[c for c in f if c.startswith("Ridge")]+["Persistence","Ground persistence"]
 f=f.dropna(subset=cols+["ground"]);out={"alignment":str(path),"targets":"real monitor","calibration":"none; all models remain CAMS-trained","periods":{}}
 for year,z in f.groupby(f.target_date.dt.year):
  bias=z.actual-z.ground
  out["periods"][str(year)]={"days":len(z),"insufficient_under_60_days":len(z)<60,"cams_reference_bias":float(bias.mean()),"cams_reference_mae":float(abs(bias).mean()),"models":{c:{"mae":float(abs(z[c]-z.ground).mean()),"rmse":float(np.sqrt(((z[c]-z.ground)**2).mean()))} for c in cols}}
 if f.empty:raise ValueError("No common monitor/forecast days")
 return out,f
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--ground",required=True);a.add_argument("--out",default="research_results/ground_research.json");v=a.parse_args();r,f=validate(v.ground);Path(v.out).write_text(json.dumps(r,indent=2));f.to_csv(Path(v.out).with_suffix(".csv"),index=False);print(json.dumps(r,indent=2))
