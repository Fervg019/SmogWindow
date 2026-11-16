import urllib.request,zipfile,io,hashlib
from pathlib import Path
url="https://zenodo.org/records/18673762/files/karachi-pk-1174872.zip?download=1"
p=Path("data/karachi");p.mkdir(parents=True,exist_ok=True)
with urllib.request.urlopen(url,timeout=60) as r:body=r.read()
if hashlib.md5(body).hexdigest()!="d06126607e9cb2642f0ab31fbe9458ef":raise ValueError("Source checksum changed; review before use")
with zipfile.ZipFile(io.BytesIO(body)) as z:
 matches=[n for n in z.namelist() if Path(n).name=="air_quality_historical.csv"]
 if len(matches)!=1:raise ValueError("Expected exactly one pollution CSV")
 (p/"air_quality_historical.csv").write_bytes(z.read(matches[0]))
(p/"SOURCE.txt").write_text(url+"\nCAMS Global via Open-Meteo, Zenodo DOI 10.5281/zenodo.18673762. Check license before redistributing source bytes.\n")
print("Karachi downloaded; now run frozen transfer test.")
