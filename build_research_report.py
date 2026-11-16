from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;R=P/"research_results"
m=json.loads((R/"weather_metrics.json").read_text());lock=m["selection"]
r=pd.read_csv(R/"reliability.csv");d=pd.read_csv(R/"dashboard_rows.csv")
fig,axs=plt.subplots(2,2,figsize=(11,9),layout="constrained")
for j,(period,title) in enumerate([("known_2025","2025 (365 days)"),("known_Jan2026","January 2026 (31 days)")]):
 a=axs[0,j];sub=r[(r.period==period)&(r.threshold==55)]
 for name,color in [(lock["probabilistic_model"],"#087f8c"),(lock["probabilistic_baseline"],"#ad5800")]:
  z=sub[(sub.model==name)&(sub.n>0)];a.plot(z.mean_probability,z.observed_frequency,"o-",color=color,label=name)
  for row in z.itertuples():a.annotate(str(row.n),(row.mean_probability,row.observed_frequency),xytext=(3,7 if color=="#087f8c" else -13),textcoords="offset points",fontsize=8,color=color)
 a.plot([0,1],[0,1],"--",color="gray");a.set(xlim=(-.03,1.05),ylim=(-.03,1.08),title=title+": chance above 55",xlabel="Predicted probability (labels = bin counts)",ylabel="Observed event fraction");a.legend(fontsize=7,loc="lower right")
 z=d[d.target_date.str.startswith("2025" if j==0 else "2026-01")];a=axs[1,j]
 obs=[(z.actual<=z[c]).mean() for c in ["q10","q50","q90"]];a.plot([.1,.5,.9],obs,"o-",color="#087f8c");a.plot([0,1],[0,1],"--",color="gray");a.set(xlim=(0,1),ylim=(0,1),xlabel="Nominal quantile",ylabel="Fraction at or below forecast",title="Quantile calibration")
fig.suptitle("SmogWindow: known benchmarks, CAMS targets (not monitors)",fontsize=14);fig.savefig(R/"probability_quality.png",dpi=160);plt.close(fig)
s=pd.read_csv(R/"conditional_performance.csv");s=s[s.period=="known_2025"];wide=s.pivot(index="group",columns="model",values="mae");gain=wide[lock["point_no_weather"]]-wide[lock["point_weather"]]
fig,a=plt.subplots(figsize=(10,6),layout="constrained");a.barh(gain.index,gain.values,color=["#087f8c" if x>=0 else "#ad5800" for x in gain]);a.axvline(0,color="black",linewidth=.8);a.set(xlabel="MAE reduction from adding lagged weather (ug/m3); positive = improvement",title="2025 conditional weather results: exploratory, overlapping groups")
fig.savefig(R/"weather_subgroups.png",dpi=160);plt.close(fig)
print("Report plots generated")
