"""Count decisions independently; retain erasures, wrong starts and regressions."""
from pathlib import Path
import json,gzip,csv,hashlib,math,importlib.util
import numpy as np
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stress_checks',HERE.parent/'offline-synthetic-stress/model_test.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def writecsv(name,rows):
 with (HERE/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def interval(errors,nbits):
 if not errors or len(errors)<2:return None
 if sum(errors)==0:return [0.,1-.05**(1/len(errors))] # Conservative zero-error trial bound.
 rates=np.array(errors)/np.array(nbits);se=float(np.std(rates,ddof=1)/np.sqrt(len(rates)))
 return [max(0.,float(np.mean(rates))-1.96*se),min(1.,float(np.mean(rates))+1.96*se)]
def wilson(k,n):
 if not n:return None
 z=1.95996398454;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;w=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return [float(c-w),float(c+w)]
def summarize():
 summary=[];patterns=[];failures=[];paired=[];audit={'stress_rows':{},'counts_reconstructed':True}
 for stage in ['detector','full']:
  with gzip.open(HERE/(stage+'-trials.jsonl.gz'),'rt') as f:rows=[json.loads(line) for line in f]
  audit['stress_rows'][stage]=len(rows)
  for row in rows:
   truth=np.unpackbits(np.frombuffer(s.frame(bytes.fromhex(row['native_hex']),row['rf_sequence']),np.uint8))
   for field,aligned in [('metrics',row['aligned']),('baseline_metrics',row['baseline_aligned'])]:
    decisions=row['decisions_hex' if field=='metrics' else 'baseline_decisions_hex']
    for method,m in row[field].items():
     calc=s.metrics(s.decoded(decisions[method]) if method in decisions else None,truth,aligned)
     assert calc==m,(stage,method)
   if stage=='full' and (not row['aligned'] or not row['baseline_aligned'] or row['metrics']['tracked']['packet_pass']!=row['baseline_metrics']['sequence']['packet_pass']):
    failures.append({key:row[key] for key in ['pattern','profile','ebn0_db','seed','trial','aligned','baseline_aligned','acquisition','metrics','baseline_metrics']})
  for bypattern,dest in [(False,summary),(True,patterns)]:
   keys=sorted(set((row['profile'],str(row['ebn0_db']),row['pattern'] if bypattern else 'all') for row in rows))
   for profile,eb,pattern in keys:
    group=[row for row in rows if row['profile']==profile and str(row['ebn0_db'])==eb and (pattern=='all' or row['pattern']==pattern)]
    methods=[('new',name) for name in ['tracked','preamble_only']]+[('baseline',name) for name in group[0]['baseline_metrics']]
    for family,method in methods:
     aligned=[row for row in group if row['aligned' if family=='new' else 'baseline_aligned']]
     ms=[row['metrics' if family=='new' else 'baseline_metrics'][method] for row in aligned]
     n=sum(m['scored_bits'] for m in ms);errors=sum(m['payload_errors'] for m in ms);packets=sum(m['packet_pass'] for m in ms)
     misses=sum(not row['acquisition']['detected'] for row in group) if family=='new' and stage=='full' else None
     dest.append(dict(stage=stage,profile=profile,ebn0_db=eb,pattern=pattern,method=method,family=family,trials=len(group),aligned=len(aligned),misses=misses,wrong_starts=len(group)-len(aligned)-misses if misses is not None else None,packets=packets,packet_wilson95=json.dumps(wilson(packets,len(group))),payload_bits=n,payload_errors=errors,conditional_payload_ber=errors/n if n else None,trial_block95=json.dumps(interval([m['payload_errors'] for m in ms],[m['scored_bits'] for m in ms])),false_changes=sum(m['false_changes'] for m in ms),missed_changes=sum(m['missed_changes'] for m in ms)))
    if not bypattern:
     common=[row for row in group if row['aligned'] and row['baseline_aligned']]
     differences=[(row['metrics']['tracked']['payload_errors']-row['baseline_metrics']['sequence']['payload_errors'])/304 for row in common]
     se=float(np.std(differences,ddof=1)/np.sqrt(len(differences))) if len(differences)>1 else None
     mean=float(np.mean(differences)) if differences else None
     paired.append(dict(stage=stage,profile=profile,ebn0_db=eb,shared_aligned=len(common),shared_bits=304*len(common),baseline_errors=sum(row['baseline_metrics']['sequence']['payload_errors'] for row in common),tracked_errors=sum(row['metrics']['tracked']['payload_errors'] for row in common),preamble_only_errors=sum(row['metrics']['preamble_only']['payload_errors'] for row in common),delta_ber=mean,paired_trial_normal95=[mean-1.96*se,mean+1.96*se] if se is not None and any(differences) else None,new_acquisitions=sum(row['aligned'] and not row['baseline_aligned'] for row in group),lost_acquisitions=sum(not row['aligned'] and row['baseline_aligned'] for row in group),packet_recoveries=sum(row['metrics']['tracked']['packet_pass'] and not row['baseline_metrics']['sequence']['packet_pass'] for row in group),packet_regressions=sum(not row['metrics']['tracked']['packet_pass'] and row['baseline_metrics']['sequence']['packet_pass'] for row in group)))
 writecsv('stress-summary.csv',summary);writecsv('pattern-summary.csv',patterns)
 (HERE/'paired-stress.json').write_text(json.dumps(paired,indent=2,allow_nan=False)+'\n');(HERE/'stress-failures-and-changes.json').write_text(json.dumps(failures,indent=2)+'\n')
 # Capture old/new exact input pairing and disjoint known-bit subset.
 old=[json.loads(line) for line in (HERE.parent/'offline-sequence-v4/trials.jsonl').read_text().splitlines()]
 new=[json.loads(line) for line in (HERE/'trials.jsonl').read_text().splitlines()];assert len(old)==len(new)==214
 rows=[];regressions=[]
 for a,b in zip(old,new):
  assert a['input_iq_sha256']==b['input_iq_sha256']
  if a['kind'] in ['negative','training']:continue
  row=dict(capture=b['capture'],kind=b['kind'],ebn0_db=b.get('ebn0_db','clean'),seed=b.get('seed'),trial=b.get('trial'),old_aligned=a['aligned_within_half_symbol'],new_aligned=b['aligned_within_half_symbol'],old_packet=a.get('frame_pass',False),new_packet=b.get('frame_pass',False))
  # The 0x55 preamble repeats, so absolute expected bits are known without replay body.
  expected=np.unpackbits(np.frombuffer(b'\x55'*32,np.uint8))
  for name,value in [('old',a),('new',b)]:
   aligned=value['aligned_within_half_symbol'];bits=s.decoded(value['decisions_hex']) if value.get('decisions_hex') else None
   row[name+'_bits156']=156 if aligned else 0;row[name+'_errors156']=int(np.sum(bits[68:224]!=expected[68:224])) if aligned else None
   row[name+'_bits184']=184 if aligned else 0;row[name+'_errors184']=value['bit_errors']
  if row['old_packet'] and not row['new_packet']:regressions.append(dict(**row,new_decisions_hex=b.get('decisions_hex'),old_decisions_hex=a.get('decisions_hex')))
  rows.append(row)
 groups=[]
 for eb in ['clean',8,12]:
  group=[row for row in rows if row['ebn0_db']==eb]
  shared=[row for row in group if row['old_aligned'] and row['new_aligned']]
  groups.append(dict(ebn0_db=eb,trials=len(group),old_aligned=sum(row['old_aligned'] for row in group),new_aligned=sum(row['new_aligned'] for row in group),old_packets=sum(row['old_packet'] for row in group),new_packets=sum(row['new_packet'] for row in group),old_bits156=sum(row['old_bits156'] for row in group),new_bits156=sum(row['new_bits156'] for row in group),old_errors156=sum(row['old_errors156'] or 0 for row in group),new_errors156=sum(row['new_errors156'] or 0 for row in group),old_bits184=sum(row['old_bits184'] for row in group),new_bits184=sum(row['new_bits184'] for row in group),old_errors184=sum(row['old_errors184'] or 0 for row in group),new_errors184=sum(row['new_errors184'] or 0 for row in group),shared_bits156=156*len(shared),shared_old_errors156=sum(row['old_errors156'] for row in shared),shared_new_errors156=sum(row['new_errors156'] for row in shared),packet_regressions=sum(row['old_packet'] and not row['new_packet'] for row in group),packet_recoveries=sum(not row['old_packet'] and row['new_packet'] for row in group)))
 writecsv('capture-paired-trials.csv',rows);writecsv('capture-comparison.csv',groups)
 (HERE/'capture-regressions.json').write_text(json.dumps(regressions,indent=2)+'\n')
 audit.update(capture_inputs_identical=214,negative_detections=sum(row['detected'] for row in new if row['kind']=='negative'),training_clean_packet=next(row.get('frame_pass',False) for row in new if row['kind']=='training'))
 selection=json.loads((HERE/'selection.json').read_text())
 for p,digest in selection['dependencies'].items():assert hashlib.sha256((HERE/p).read_bytes()).hexdigest()==digest,p
 audit['frozen_dependencies_unchanged']=len(selection['dependencies'])
 (HERE/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 print(json.dumps(dict(captures=groups,audit=audit),indent=2))
if __name__=='__main__':summarize()
