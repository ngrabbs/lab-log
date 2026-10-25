"""Independent paired gate/control counts, all failures retained."""
from pathlib import Path
import json,gzip,csv
import numpy as np
H=Path(__file__).resolve().parent

def delta_interval(d):
 if len(d)<2 or not any(d):return None
 mean=float(np.mean(d));se=float(np.std(d,ddof=1)/np.sqrt(len(d)))
 return [mean-1.96*se,mean+1.96*se]
def main():
 results=[];changes=[]
 for stage in ['detector','full']:
  with gzip.open(H/(stage+'-trials.jsonl.gz'),'rt') as f:rows=[json.loads(line) for line in f]
  keys=sorted(set((r['profile'],str(r['ebn0_db'])) for r in rows))
  for profile,eb in keys:
   group=[r for r in rows if r['profile']==profile and str(r['ebn0_db'])==eb]
   aligned=[r for r in group if r['aligned']]
   for control in ['continuous','preamble_only']:
    diff=[(r['metrics']['gated']['payload_errors']-r['metrics'][control]['payload_errors'])/304 for r in aligned]
    results.append(dict(stage=stage,profile=profile,ebn0_db=eb,control=control,trials=len(group),shared_aligned=len(aligned),shared_bits=304*len(aligned),gate_enabled=sum(r['tracking']['tracking_enabled'] for r in group if 'tracking' in r),gated_errors=sum(r['metrics']['gated']['payload_errors'] for r in aligned),control_errors=sum(r['metrics'][control]['payload_errors'] for r in aligned),delta_ber=float(np.mean(diff)) if diff else None,paired_trial_normal95=delta_interval(diff),gated_packets=sum(r['metrics']['gated']['packet_pass'] for r in group),control_packets=sum(r['metrics'][control]['packet_pass'] for r in group),packet_recoveries=sum(r['metrics']['gated']['packet_pass'] and not r['metrics'][control]['packet_pass'] for r in group),packet_regressions=sum(not r['metrics']['gated']['packet_pass'] and r['metrics'][control]['packet_pass'] for r in group)))
  for r in rows:
   if any(r['metrics']['gated']['packet_pass']!=r['metrics'][c]['packet_pass'] for c in ['continuous','preamble_only']):
    changes.append(dict(stage=stage,**{k:r[k] for k in ['pattern','profile','ebn0_db','seed','trial','aligned','tracking','metrics','decisions_hex']}))
 (H/'gate-vs-controls.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
 with (H/'packet-control-changes.jsonl.gz').open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as dest:
  for row in changes:dest.write((json.dumps(row,separators=(',',':'))+'\n').encode())
 capture=list(csv.DictReader((H/'capture-paired-trials.csv').open()));summary=[]
 for cap in ['libre02','pluto00','pluto20']:
  for eb in ['clean','8','12']:
   rows=[r for r in capture if r['capture']==cap and str(r['ebn0_db'])==eb]
   summary.append(dict(capture=cap,ebn0_db=eb,trials=len(rows),gate_enabled=sum(r['gate_enabled']=='True' for r in rows),v4_packets=sum(r['old_packet']=='True' for r in rows),continuous_packets=sum(r['continuous_packet']=='True' for r in rows),preamble_only_packets=sum(r['preamble_only_packet']=='True' for r in rows),gated_packets=sum(r['new_packet']=='True' for r in rows),min_drift_hz_s=min(float(r['drift_rate_hz_s']) for r in rows),max_drift_hz_s=max(float(r['drift_rate_hz_s']) for r in rows)))
 with (H/'capture-by-source.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
 print('paired summaries',len(results),'packet changed rows',len(changes))
 for eb in ['8','12','clean']:
  for control in ['continuous','preamble_only']:
   rs=[r for r in results if r['stage']=='full' and r['ebn0_db']==eb and r['control']==control]
   print('full',eb,control,{k:sum(r[k] for r in rs) for k in ['gated_packets','control_packets','packet_recoveries','packet_regressions']})
if __name__=='__main__':main()
