"""Download documented public OpenAQ S3 objects; no credentials required."""
import argparse, gzip, io, json, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from prepare_ground import prepare
BASE="https://openaq-data-archive.s3.amazonaws.com/"
def fetch(years,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);frames=[];sources=[]
 for year in years:
  token=None
  while True:
   params={"list-type":"2","prefix":f"records/csv.gz/locationid=8664/year={year}/"}
   if token:params["continuation-token"]=token
   with urllib.request.urlopen(BASE+"?"+urllib.parse.urlencode(params),timeout=30) as r:root=ET.fromstring(r.read())
   ns={"s":"http://s3.amazonaws.com/doc/2006-03-01/"}
   for node in root.findall("s:Contents",ns):
    key=node.findtext("s:Key",namespaces=ns)
    if not key.endswith(".csv.gz"):continue
    dest=out/Path(key).name
    if not dest.exists():
     with urllib.request.urlopen(BASE+urllib.parse.quote(key,safe="/="),timeout=30) as r:body=r.read()
     gzip.decompress(body);dest.write_bytes(body)
    df=pd.read_csv(dest,compression="gzip");df=df[(df.parameter=="pm25")&(df.location_id==8664)]
    if len(df):
     if not df.units.isin(["µg/m³","ug/m3","µg/m3"]).all():raise ValueError("Unexpected concentration units")
     frames.append(df);sources.append(BASE+key)
   token=root.findtext("s:NextContinuationToken",namespaces=ns)
   if not token:break
 if not frames:raise ValueError("No PM2.5 objects found: absence is not zero pollution")
 df=pd.concat(frames,ignore_index=True).drop_duplicates()
 if df.sensor_id.nunique()!=1:raise ValueError("Multiple sensors: resolve instrument history before merging")
 df.to_csv(out/"monitor_hourly.csv",index=False)
 for tz,name in [("UTC","utc"),("Asia/Karachi","local")]:
  prepare(df,"datetime","value","Asia/Karachi",tz).to_csv(out/f"ground_daily_{name}.csv")
 (out/"provenance.json").write_text(json.dumps({"location_id":8664,"sources":sources,"rows":len(df),"qc":"Archive values; negative codes excluded. Source QA status must be reviewed.","units":"ug/m3"},indent=2))
 print("Downloaded",len(df),"monitor rows; UTC/local alignment must both be reviewed.")
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--years",nargs="+",type=int,default=[2023,2024,2025]);a.add_argument("--out",default="data/monitor");v=a.parse_args();fetch(v.years,v.out)
