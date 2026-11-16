"""Compare daily issued CAMS forecasts on equal dates; never infer issue time.
Input columns: origin_date,target_date,issued_at,available_at,decision_at,pm2_5,units.
Daily aggregates must already represent the same daily boundary as research targets.
"""
import argparse,json
from pathlib import Path
import pandas as pd
import numpy as np
P=Path(__file__).resolve().parent
def compare(path):
 c=pd.read_csv(path)
 if not c.units.eq("ug/m3").all():raise ValueError("Explicit ug/m3 required")
 for col in ["issued_at","available_at","decision_at"]:
  if not c[col].astype(str).str.contains(r"Z$|[+-]\d\d:\d\d$",regex=True).all():raise ValueError("Timezone required: "+col)
  c[col]=pd.to_datetime(c[col],utc=True)
 if (c.issued_at>c.available_at).any() or (c.available_at>c.decision_at).any():raise ValueError("Unavailable at decision time")
 if c.target_date.duplicated().any():raise ValueError("One preselected issue per target day required")
 target=pd.to_datetime(c.target_date,utc=True)
 if (c.decision_at>=target).any():raise ValueError("Decision must precede target UTC day")
 if not ((pd.to_datetime(c.target_date)-pd.to_datetime(c.origin_date)).dt.days==1).all():raise ValueError("Expected next-day forecasts")
 if not np.isfinite(c.pm2_5).all() or (c.pm2_5<0).any():raise ValueError("Invalid forecast concentrations")
 f=pd.read_csv(P/"research_results/all_point_predictions.csv");z=f.merge(c,on=["origin_date","target_date"],validate="one_to_one")
 if z.empty:raise ValueError("No common evaluation days")
 names=[x for x in f if x.startswith("Ridge")]+["Persistence","pm2_5"]
 return {"days":len(z),"verification_target":"CAMS modeled series, not monitor; independence limitation remains","mae":{n:float(abs(z[n]-z.actual).mean()) for n in names}}
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("csv");a.add_argument("--out",default="research_results/issued_cams_comparison.json");v=a.parse_args();r=compare(v.csv);Path(v.out).write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
