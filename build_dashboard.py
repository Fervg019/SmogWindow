"""Build SmogWindow_dashboard.html: one offline file (no server, no network, no libraries). Run after run_all.py."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / 'results'


def build():
    m = json.loads((R / 'metrics.json').read_text()); fz = m['frozen']; model = fz['forecast_model']
    wf = pd.read_csv(R / 'walkforward_predictions.csv', parse_dates=['target_date', 'origin_date'])
    rows = wf[wf.target_date >= '2025-01-01'].reset_index(drop=True)
    raw = pd.read_csv(ROOT / 'data/air_quality_historical.csv', parse_dates=['date']).set_index('date').pm2_5
    raw = raw[raw.index >= '2024-11-01']
    def r1(v): return round(float(v), 2)
    out_rows = [{'o': a.strftime('%Y-%m-%d'), 't': t.strftime('%Y-%m-%d'), 'a': r1(act), 'p0': r1(p0), 'm': r1(mm), 'lo': r1(lo), 'hi': r1(hi),
                 'ms': [r1(x) for x in (s1, s3, s5)], 'ps': [r1(x) for x in (q1, q3, q5)], 'ab': int(ab), 'w': '2025' if t.year == 2025 else '2026'}
                for a, t, act, p0, mm, lo, hi, s1, s3, s5, q1, q3, q5, ab in zip(
                    rows.origin_date, rows.target_date, rows.actual, rows['Persistence'], rows[model], rows.model_lo, rows.model_hi,
                    rows.model_s1, rows.model_s3, rows.model_s5, rows.persistence_s1, rows.persistence_s3, rows.persistence_s5, rows.abrupt_change_today)]
    def win(k, label):
        w = m[k]
        return {'label': label, 'n': w['n'], 'mae_model': r1(w['forecast'][model]['mae']), 'mae_persistence': r1(w['forecast']['Persistence']['mae']),
                'gain_pct': r1(w['mae_gain_pct']), 'gain_ci': [r1(v) for v in w['mae_gain_ci95']], 'interval': w['interval']['model'],
                'groups': {g: v['model'] for g, v in w['interval_by_group'].items()}, 'sens': w['decision_sensitivity'], 'abrupt': w['abrupt']}
    data = {'model': model, 'scheme': fz['uncertainty_label'], 'rows': out_rows, 'series': {'d': [d.strftime('%Y-%m-%d') for d in raw.index], 'v': [None if pd.isna(v) else r1(v) for v in raw.values]},
            'win': {'2025': win('benchmark_2025', '2025 (known benchmark)'), '2026': win('holdout_2026', 'Jan 1 - Feb 18, 2026 (new holdout)')},
            'dev': {'n': m['dev']['n'], 'gain_pct': r1(m['dev']['mae_gain_pct'])}, 'abrupt': {'cut': r1(fz['abrupt_cutoff']), 'dev_supported': fz['abrupt_flag_supported_on_dev']},
            'pooled': m['pooled_2025_2026_decision']}
    html = TEMPLATE.replace('/*DATA*/', 'const D=' + json.dumps(data, separators=(',', ':')) + ';')
    (ROOT / 'SmogWindow_dashboard.html').write_text(html, encoding='utf-8')
    return len(html)


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SmogWindow | Lahore planning replay</title>
<style>
:root{--bg:#f6f8fb;--card:#fff;--ink:#0f172a;--mute:#5b6b80;--line:#dbe3ec;--teal:#0d9488;--navy:#172554;--warn:#b45309;--bad:#b91c1c;--ok:#15803d;--chip:#eef2f7}
@media(prefers-color-scheme:dark){:root{--bg:#0b1220;--card:#121c2e;--ink:#e8eef6;--mute:#9db0c5;--line:#25354d;--teal:#2dd4bf;--navy:#93c5fd;--warn:#fbbf24;--bad:#f87171;--ok:#4ade80;--chip:#1a2740}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:22px 16px 60px}
h1{font-size:28px;margin:4px 0 2px;letter-spacing:-.02em}h2{font-size:16px;margin:0 0 10px}
.eyebrow{color:var(--teal);font-weight:700;letter-spacing:.12em;font-size:12px}
.banner{background:var(--chip);border:1px solid var(--line);border-left:4px solid var(--warn);padding:10px 14px;border-radius:8px;color:var(--mute);margin:12px 0 18px;font-size:13.5px}
.banner b{color:var(--ink)}
.controls{display:flex;flex-wrap:wrap;gap:14px;align-items:end;margin-bottom:16px}
label{display:block;font-size:12px;color:var(--mute);margin-bottom:4px}
input,select,button{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
button{cursor:pointer}button:hover{border-color:var(--teal)}button.primary{background:var(--teal);color:#04201d;border-color:var(--teal);font-weight:600}
.grid{display:grid;gap:14px;grid-template-columns:repeat(12,1fr)}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.c4{grid-column:span 4}.c5{grid-column:span 5}.c6{grid-column:span 6}.c7{grid-column:span 7}.c8{grid-column:span 8}.c12{grid-column:span 12}
@media(max-width:820px){.c4,.c5,.c6,.c7,.c8{grid-column:span 12}}
.flag{font-size:22px;font-weight:700;margin:2px 0 6px}.flag.yes{color:var(--warn)}.flag.no{color:var(--ok)}
.big{font-size:30px;font-weight:700;letter-spacing:-.02em}.mute{color:var(--mute)}.small{font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13.5px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:right}th:first-child,td:first-child{text-align:left}th{color:var(--mute);font-weight:600}
tr.hl td{font-weight:700;color:var(--teal)}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;background:var(--chip);color:var(--mute);margin:2px 4px 2px 0}.pill.bad{color:var(--bad)}.pill.ok{color:var(--ok)}.pill.warn{color:var(--warn)}
svg text{fill:var(--mute);font-size:11px}svg .t{fill:var(--ink)}
textarea{width:100%;min-height:210px;font:12.5px/1.5 ui-monospace,Consolas,monospace;resize:vertical}
.bars{display:grid;gap:8px}.bar{display:grid;grid-template-columns:150px 1fr 60px;gap:8px;align-items:center;font-size:13px}.track{position:relative;height:14px;background:var(--chip);border-radius:7px}.fill{height:100%;border-radius:7px;background:var(--teal)}.fill.low{background:var(--warn)}.mark{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--ink)}
details{margin-top:8px}summary{cursor:pointer;color:var(--mute)}
footer{margin-top:22px;color:var(--mute);font-size:12.5px}
@media print{body{background:#fff;color:#000}.controls,button,footer,.noprint{display:none!important}.card{break-inside:avoid;border-color:#999}textarea{border:0}}
</style></head><body><div class="wrap">
<div class="eyebrow">SMOGWINDOW / LAHORE</div>
<h1>Plan with uncertainty and baselines in view.</h1>
<div class="banner"><b>Historical replay of modeled data, not live monitoring.</b> Values are CAMS atmospheric-model estimates for Lahore (not a school or monitor reading). A planning flag means &ldquo;prepare an alternative&rdquo;; no flag is <b>not</b> a safety clearance. Research prototype: not medical advice, not validated by any school.</div>

<div class="controls">
 <div><label for="date">Forecast origin (day just completed)</label><div style="display:flex;gap:6px"><button id="prev" aria-label="Previous day">&larr;</button><input type="date" id="date"><button id="next" aria-label="Next day">&rarr;</button></div></div>
 <div><label for="thr">Planning threshold (&micro;g/m&sup3;, illustrative)</label><select id="thr"><option>35</option><option selected>55</option><option>100</option></select></div>
 <div><label for="ratio">A missed high day costs ... false alarms</label><select id="ratio"><option value="1">1&times;</option><option value="3" selected>3&times;</option><option value="5">5&times;</option></select></div>
 <div><label>&nbsp;</label><button id="reveal">Reveal next-day reference</button></div>
 <div><label>&nbsp;</label><button id="example">Jump to a missed spike</button></div>
</div>

<div class="grid">
 <div class="card c5"><h2>Planning flag for <span id="tgt"></span></h2><div id="flag" class="flag"></div><div id="flagnote" class="small mute"></div>
  <div style="margin-top:12px" class="big"><span id="fc"></span> <span class="small mute">&micro;g/m&sup3; forecast daily mean</span></div>
  <div class="small mute" id="rng"></div><div id="agree" style="margin-top:10px"></div><div id="outcome" style="margin-top:10px"></div></div>
 <div class="card c7"><h2>Recent history, forecast and uncertainty</h2><svg id="chart" viewBox="0 0 760 300" width="100%" role="img" aria-label="Chart of recent PM2.5 and next-day forecast"></svg>
  <div class="small mute" id="chartnote"></div></div>

 <div class="card c6"><h2>Same day, four warning policies</h2><table id="pol"></table><div class="small mute" style="margin-top:8px">&ldquo;+ margin&rdquo; adds an error margin learned from earlier forecast errors for the chosen cost ratio. Persistence = assume tomorrow equals today.</div></div>
 <div class="card c6"><h2>Data checks for this forecast</h2><div id="dq"></div></div>

 <div class="card c7"><h2>Track record over a replay window <select id="win" style="float:right;font-size:13px"><option value="2025">2025 (known benchmark)</option><option value="2026">Jan&ndash;Feb 2026 (new holdout)</option></select></h2>
  <table id="rec"></table><div id="recnote" class="small" style="margin-top:10px"></div></div>
 <div class="card c5"><h2>Is the 80% range trustworthy?</h2><div id="rel" class="bars"></div><div class="small mute" id="relnote" style="margin-top:10px"></div></div>

 <div class="card c12"><h2>Exportable planning summary</h2><textarea id="sum" readonly aria-label="Planning summary text"></textarea>
  <div class="noprint" style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><button class="primary" id="copy">Copy</button><button id="dl">Download .txt</button><button id="print">Print / save PDF</button><span id="copied" class="small mute"></span></div></div>
</div>
<details class="card" style="margin-top:14px"><summary>What is established, and what is not</summary><div class="small" id="honest"></div></details>
<footer>Data: Kulkarni &amp; Tawade, Zenodo 10.5281/zenodo.18673725 (CAMS via Open-Meteo). Forecasts are walk-forward: each month the model is refit on earlier days only. Method details are in METHODS.md in the project folder.</footer>
</div>
<script>
/*DATA*/
const $=id=>document.getElementById(id);
const rows=D.rows, byO=Object.fromEntries(rows.map((r,i)=>[r.o,i])), ser=Object.fromEntries(D.series.d.map((d,i)=>[d,D.series.v[i]]));
let idx=byO['2025-05-21'], revealed=false;
const fmt=v=>Math.round(v);
function addDays(s,n){const d=new Date(s+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10)}
function policy(r,thr,ri){return{'Model + margin':r.ms[ri]>thr,'Persistence + margin':r.ps[ri]>thr,'Model (no margin)':r.m>thr,'Persistence (no margin)':r.p0>thr}}
function dq(r){const flags=[];let miss=0;for(let k=0;k<14;k++){if(ser[addDays(r.o,-k)]==null)miss++}
 flags.push(miss?['bad',miss+' of the last 14 days have no PM2.5 value: a forecast could not be issued.']:['ok','14-day input window complete (14/14 days).']);
 flags.push(r.ab?['warn','Abrupt change today (more than '+D.abrupt.cut+' \u00b5g/m\u00b3 vs yesterday). Next-day errors were larger after abrupt changes in the development period and in 2025, but not in Jan\u2013Feb 2026 (weak evidence): treat the forecast with extra caution.']:['ok','No abrupt change today.']);
 if(r.p0>200)flags.push(['warn','Today is extremely polluted ('+fmt(r.p0)+' \u00b5g/m\u00b3); forecasts for extreme days are least tested.']);
 flags.push(['warn','Source is a modeled grid estimate, not a monitor or school measurement. No ground-monitor validation has been done.']);return flags}
function summary(r,thr,ratio,ri){const pol=policy(r,thr,ri),a=pol['Model + margin'],b=pol['Persistence + margin'];
 const L=['SmogWindow planning summary - Lahore, PM2.5 (modeled, historical replay)','Forecast origin: '+r.o+'   Forecast for: '+r.t,
 'Forecast daily mean: '+fmt(r.m)+' ug/m3   80% range: '+fmt(r.lo)+'-'+fmt(r.hi)+' ug/m3   (method: '+D.scheme+')','Persistence (tomorrow = today): '+fmt(r.p0)+' ug/m3',
 'Assumptions: threshold '+thr+' ug/m3; a missed high day is '+ratio+'x as costly as a false alarm (illustrative, not a regulation).',
 'Planning flag (model + margin): '+(a?'YES - prepare an indoor / alternative plan':'NO flag at these settings (this is not a safety clearance)'),
 'Calibrated-persistence flag: '+(b?'YES':'NO')+(a!==b?'   <-- the two methods disagree':'')];
 dq(r).forEach(f=>{if(f[0]!=='ok')L.push('Check: '+f[1])});
 if(revealed)L.push('Outcome (evaluation only): reference value was '+fmt(r.a)+' ug/m3.');
 L.push('Limits:','- Modeled CAMS estimates, not measurements at a school or a monitor.','- No flag does NOT mean outdoor activity is safe. Check official guidance and current local readings.','- Research prototype: not medical advice; not validated by any school.');return L.join('\n')}
function chart(r,thr){const days=45,x0=44,x1=730,H=300,top=16,bot=34;const ds=[];for(let k=days-1;k>=0;k--)ds.push(addDays(r.o,-k));
 const vals=ds.map(d=>ser[d]);const ymax=Math.max(thr*1.25,r.hi,r.a*(revealed?1:0),...vals.filter(v=>v!=null))*1.08;
 const X=i=>x0+(x1-x0)*i/days,Y=v=>H-bot-(H-bot-top)*v/ymax;let s='';
 for(let t=0;t<=ymax;t+=Math.ceil(ymax/5/10)*10){s+=`<line x1="${x0}" x2="${x1+20}" y1="${Y(t)}" y2="${Y(t)}" stroke="var(--line)"/><text x="${x0-6}" y="${Y(t)+4}" text-anchor="end">${t}</text>`}
 s+=`<line x1="${x0}" x2="${x1+20}" y1="${Y(thr)}" y2="${Y(thr)}" stroke="var(--warn)" stroke-dasharray="5 4"/><text x="${x0+4}" y="${Y(thr)-5}" style="fill:var(--warn)">threshold ${thr}</text>`;
 let pts=vals.map((v,i)=>v==null?null:[X(i),Y(v)]);let path='',pen=false;pts.forEach(p=>{if(!p){pen=false;return}path+=(pen?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1);pen=true});
 s+=`<path d="${path}" fill="none" stroke="var(--navy)" stroke-width="2"/>`;
 [0,14,29].forEach(k=>{if(k<days)s+=`<text x="${X(k)}" y="${H-bot+16}" text-anchor="middle">${ds[k].slice(5)}</text>`});
 const tx=X(days)+14;s+=`<text x="${tx}" y="${H-bot+16}" text-anchor="middle">${r.t.slice(5)}</text>`;
 s+=`<line x1="${X(days-1)}" y1="${Y(vals[days-1])}" x2="${tx}" y2="${Y(r.m)}" stroke="var(--teal)" stroke-dasharray="3 3"/>`;
 s+=`<line x1="${tx}" x2="${tx}" y1="${Y(r.lo)}" y2="${Y(r.hi)}" stroke="var(--teal)" stroke-width="7" opacity=".35" stroke-linecap="round"/><circle cx="${tx}" cy="${Y(r.m)}" r="5.5" fill="var(--teal)"><title>Model forecast ${fmt(r.m)}</title></circle>`;
 s+=`<circle cx="${tx}" cy="${Y(r.p0)}" r="4.5" fill="none" stroke="var(--mute)" stroke-width="2"><title>Persistence ${fmt(r.p0)}</title></circle>`;
 if(revealed)s+=`<path d="M${tx} ${Y(r.a)-7}L${tx+7} ${Y(r.a)}L${tx} ${Y(r.a)+7}L${tx-7} ${Y(r.a)}Z" fill="var(--bad)"><title>Reference ${fmt(r.a)}</title></path>`;
 s+=`<g transform="translate(${x0+6},${top+4})"><text x="0" y="0">navy line: modeled PM2.5 history &nbsp; teal: forecast with 80% range &nbsp; hollow: persistence${revealed?' &nbsp; red: reference':''}</text></g>`;
 $('chart').innerHTML=s;$('chartnote').textContent='Range width is '+fmt(r.hi-r.lo)+' \u00b5g/m\u00b3 around the forecast: the forecast is not precise.'}
function render(){const r=rows[idx],thr=+$('thr').value,ratio=+$('ratio').value,ri=[1,3,5].indexOf(ratio),pol=policy(r,thr,ri),yes=pol['Model + margin'];
 $('date').value=r.o;$('tgt').textContent=r.t;$('flag').className='flag '+(yes?'yes':'no');$('flag').textContent=yes?'Prepare an alternative plan':'No planning flag';
 $('flagnote').textContent=yes?'Model forecast plus its learned error margin exceeds '+thr+' \u00b5g/m\u00b3.':'Not a safety clearance: it only means the forecast plus margin stays under '+thr+'.';
 $('fc').textContent=fmt(r.m);$('rng').textContent='80% range '+fmt(r.lo)+'\u2013'+fmt(r.hi)+' \u00b5g/m\u00b3 \u00b7 persistence '+fmt(r.p0)+' \u00b7 method: '+D.scheme;
 $('agree').innerHTML=pol['Model + margin']===pol['Persistence + margin']?'<span class="pill ok">Model and calibrated persistence agree</span>':'<span class="pill warn">Model and calibrated persistence disagree on this day</span>';
 const truth=r.a>thr;$('outcome').innerHTML=revealed?`<span class="pill ${truth?'bad':'ok'}">Reference: ${fmt(r.a)} \u00b5g/m\u00b3 (${truth?'above':'below'} threshold)</span> <span class="pill ${yes===truth?'ok':'bad'}">${yes===truth?'correct':(yes?'false alarm':'missed high day')}</span>`:'<span class="small mute">Next-day reference hidden until you reveal it.</span>';
 $('reveal').textContent=revealed?'Hide reference':'Reveal next-day reference';
 let t='<tr><th>Policy</th><th>Flag</th>'+(revealed?'<th>Result</th>':'')+'</tr>';for(const k in pol){const res=pol[k]===truth?'correct':(pol[k]?'false alarm':'missed');t+=`<tr${k==='Model + margin'?' class="hl"':''}><td>${k}</td><td>${pol[k]?'prepare':'no flag'}</td>${revealed?`<td>${res}</td>`:''}</tr>`}$('pol').innerHTML=t;
 $('dq').innerHTML=dq(r).map(f=>`<div class="pill ${f[0]}" style="display:block;border-radius:8px;padding:7px 10px;margin:0 0 6px">${f[1]}</div>`).join('');
 chart(r,thr);$('sum').value=summary(r,thr,ratio,ri);record();}
function record(){const thr=+$('thr').value,ratio=+$('ratio').value,ri=[1,3,5].indexOf(ratio),w=$('win').value,W=D.win[w],rs=rows.filter(r=>r.w===w);
 const pols={'Never flag':r=>false,'Always flag':r=>true,'Persistence (no margin)':r=>r.p0>thr,'Persistence + margin':r=>r.ps[ri]>thr,'Model (no margin)':r=>r.m>thr,'Model + margin':r=>r.ms[ri]>thr};
 let t='<tr><th>Policy ('+rs.length+' days)</th><th>Missed</th><th>False alarms</th><th>Flagged</th><th>Cost*</th></tr>';const cost={};
 for(const k in pols){let fn=0,fp=0,fl=0;rs.forEach(r=>{const a=r.a>thr,f=pols[k](r);if(f)fl++;if(a&&!f)fn++;if(!a&&f)fp++});cost[k]=ratio*fn+fp;t+=`<tr${k==='Model + margin'?' class="hl"':''}><td>${k}</td><td>${fn}</td><td>${fp}</td><td>${fl}</td><td>${cost[k]}</td></tr>`}
 $('rec').innerHTML=t;const s=W.sens.find(x=>x.threshold===thr&&x.ratio===ratio),adv=cost['Persistence + margin']-cost['Model + margin'],lo=s.advantage_ci95_per_day[0]*W.n,hi=s.advantage_ci95_per_day[1]*W.n;
 const sig=lo>0?'The model\u2019s advantage over calibrated persistence is unlikely to be zero in this window.':(hi<0?'Calibrated persistence did reliably better in this window.':'This is <b>not distinguishable</b> from no difference.');
 $('recnote').innerHTML=`*Cost = ${ratio} \u00d7 missed + false alarms (illustrative units). <b>Model + margin vs persistence + margin:</b> ${adv>=0?'+':''}${adv} cost units in favour of the model (95% block-bootstrap range ${Math.round(lo)} to ${Math.round(hi)}). ${sig}<br>Forecast error: model ${W.mae_model} vs persistence ${W.mae_persistence} \u00b5g/m\u00b3 MAE (${W.gain_pct}% better; 95% range of the gain ${W.gain_ci[0]}\u2013${W.gain_ci[1]} \u00b5g/m\u00b3). Changing the controls re-reads results; it is not retuning.`;
 let b='';for(const g in W.groups){const c=W.groups[g].coverage;b+=`<div class="bar"><div>${g} <span class="mute">(${W.groups[g].n} d)</span></div><div class="track"><div class="fill ${Math.abs(c-.8)>.07?'low':''}" style="width:${c*100}%"></div><div class="mark" style="left:80%"></div></div><div>${Math.round(c*100)}%</div></div>`}
 $('rel').innerHTML=b;$('relnote').textContent='Black mark = 80% target. Overall coverage '+Math.round(W.interval.coverage*100)+'% in this window; amber bars miss the target by more than 7 points. Few days in a group means a noisy estimate.';}
function go(i){idx=Math.max(0,Math.min(rows.length-1,i));render()}
$('prev').onclick=()=>go(idx-1);$('next').onclick=()=>go(idx+1);$('date').onchange=e=>{if(byO[e.target.value]!=null)go(byO[e.target.value])};
$('date').min=rows[0].o;$('date').max=rows[rows.length-1].o;$('thr').onchange=render;$('ratio').onchange=render;$('win').onchange=record;
$('reveal').onclick=()=>{revealed=!revealed;render()};document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT'||e.target.tagName==='TEXTAREA')return;if(e.key==='ArrowLeft')go(idx-1);if(e.key==='ArrowRight')go(idx+1)});
$('example').onclick=()=>{const thr=+$('thr').value,ri=[1,3,5].indexOf(+$('ratio').value);const c=rows.map((r,i)=>[i,r]).filter(([i,r])=>r.a>thr&&!(r.ms[ri]>thr));const worst=c.sort((a,b)=>(b[1].a-b[1].ms[ri])-(a[1].a-a[1].ms[ri]))[0];if(worst){revealed=true;go(worst[0])}};
$('copy').onclick=()=>{$('sum').select();(navigator.clipboard?navigator.clipboard.writeText($('sum').value):Promise.reject()).then(()=>$('copied').textContent='Copied.',()=>{document.execCommand('copy');$('copied').textContent='Copied.'})};
$('dl').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([$('sum').value],{type:'text/plain'}));a.download='smogwindow_plan_'+rows[idx].t+'.txt';a.click()};$('print').onclick=()=>window.print();
$('honest').innerHTML=`<p><b>Established (on modeled data):</b> a walk-forward ridge forecast was ${D.dev.gain_pct}% (development), ${D.win['2025'].gain_pct}% (2025) and ${D.win['2026'].gain_pct}% (Jan&ndash;Feb 2026) more accurate than &ldquo;tomorrow = today&rdquo;. Learned error margins make warnings far more sensitive than raw persistence.</p><p><b>Not established:</b> that the ML warning beats <i>calibrated</i> persistence (differences are small; see the intervals above), performance on real monitors, an operational live workflow, or any school&rsquo;s actual costs and thresholds.</p>`;
render();
</script></body></html>
'''

if __name__ == '__main__':
    print('wrote SmogWindow_dashboard.html', build(), 'bytes')
