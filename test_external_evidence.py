import tempfile,unittest
from pathlib import Path
import pandas as pd
from prepare_ground import prepare
from compare_issued_forecasts import compare
from validate_research_ground import validate

class EvidenceTests(unittest.TestCase):
 def test_timezone_and_unique_hours(self):
  d=pd.DataFrame({"t":pd.date_range("2025-01-01",periods=24,freq="h"),"v":range(24)})
  local=prepare(d,"t","v","Asia/Karachi","Asia/Karachi")
  utc=prepare(d,"t","v","Asia/Karachi","UTC")
  self.assertEqual(local.iloc[0].valid_hours,24);self.assertEqual(utc.iloc[0].valid_hours,19)
  with self.assertRaises(ValueError):prepare(pd.concat([d,d.iloc[:1]]),"t","v","UTC","UTC")
 def test_late_issue_rejected(self):
  d=pd.DataFrame([dict(origin_date="2024-12-31",target_date="2025-01-01",issued_at="2024-12-31T20:00Z",available_at="2024-12-31T22:00Z",decision_at="2024-12-31T21:00Z",pm2_5=100,units="ug/m3")])
  with tempfile.TemporaryDirectory() as t:
   f=Path(t)/"test.csv";d.to_csv(f,index=False)
   with self.assertRaisesRegex(ValueError,"Unavailable"):compare(f)
   d["available_at"]="2024-12-31T20:30Z";d.to_csv(f,index=False)
   self.assertEqual(compare(f)["days"],1)
 def test_ground_exact_pairing(self):
  d=pd.DataFrame({"date":pd.date_range("2024-12-30",periods=5),"pm2_5":[10,20,30,40,50]})
  with tempfile.TemporaryDirectory() as t:
   f=Path(t)/"test.csv";d.to_csv(f,index=False);r,rows=validate(f)
   self.assertTrue((rows.ground-rows["Ground persistence"]==10).all())
   self.assertTrue(all(x["insufficient_under_60_days"] for x in r["periods"].values()))
if __name__=="__main__":unittest.main()
