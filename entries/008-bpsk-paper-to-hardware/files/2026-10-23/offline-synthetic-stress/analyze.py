"""Recount truth/decisions, retain erasures, summarize fixed synthetic budgets."""
import gzip,json,csv,math,sys
import numpy as np
from model_test import *
from diagnostic import cluster_interval

def wilson(k,n):
 z=1.95996398454;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return max(0,c-h),min(1,c+h)
def table(name,rows):
 with (HERE/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main(stage):
 rows=[json.loads(x) for x in gzip.open(HERE/(stage+'-trials.jsonl.gz'),'rt')]
 assert len(rows)==(3240 if stage=='detector' else 570)
 for row in rows:
    truth=np.unpackbits(np.frombuffer(frame(bytes.fromhex(row['native_hex']),row['rf_sequence']),np.uint8))
    for name,m in row['metrics'].items():
      bits=decoded(row['decisions_hex'][name]) if name in row['decisions_hex'] else None
      assert metrics(bits,truth,row['aligned'])==m,(row['pattern'],row['profile'],name)
    if stage=='full' and row['acquisition']['detected']:
      assert abs(row['acquisition']['start_sample']-row['true_start_sample'])<=20 or not row['aligned']
      assert decoded(row['acquisition']['baseline_decisions_hex']).tolist()==decoded(row['decisions_hex']['pair']).tolist()
      assert decoded(row['acquisition']['sign_decisions_hex']).tolist()==decoded(row['decisions_hex']['sign']).tolist()
 summary=[];paired=[]
 for pattern in PATTERNS+['ALL']:
  for profile in (PROFILES if stage=='detector' else FULL_PROFILES):
   for eb in ([4,8,12] if stage=='detector' else [8,12,'clean']):
    group=[r for r in rows if (pattern=='ALL' or r['pattern']==pattern) and r['profile']==profile and r['ebn0_db']==eb]
    if not group:continue
    methods=group[0]['metrics'].keys()
    for name in methods:
      scored=[r for r in group if r['metrics'][name]['scored_bits']];errors=[r['metrics'][name]['payload_errors'] for r in scored]
      ber,lo,hi,method=cluster_interval(errors,304) if len(errors)>1 else (sum(errors)/(len(errors)*304) if errors else None,None,None,'At most one aligned trial; no BER interval estimated')
      zero=sum(r['metrics'][name].get('zero_bits',0) for r in scored);one=sum(r['metrics'][name].get('one_bits',0) for r in scored)
      false=sum(r['metrics'][name].get('false_changes',0) for r in scored);missed=sum(r['metrics'][name].get('missed_changes',0) for r in scored)
      packets=sum(r['metrics'][name]['packet_pass'] for r in group)
      summary.append(dict(stage=stage,pattern=pattern,profile=profile,ebn0_db=eb,detector=name,trials=len(group),aligned=len(scored),
        misses=sum(not r.get('acquisition',{}).get('detected',True) for r in group),wrong_start=sum(r.get('acquisition',{}).get('detected',False) and not r['aligned'] for r in group),
        payload_bits=len(scored)*304,payload_errors=sum(errors),payload_ber=ber,ber95_low=lo,ber95_high=hi,ber_interval_method=method,
        zero_bits=zero,one_bits=one,false_changes=false,missed_changes=missed,false_change_ber=false/zero if zero else None,missed_change_ber=missed/one if one else None,
        payload_exact=sum(r['metrics'][name].get('payload_exact',False) for r in group),packets=packets,packet_wilson95_low=wilson(packets,len(group))[0],packet_wilson95_high=wilson(packets,len(group))[1],
        mean_payload_symbol_energy=float(np.mean([r['payload_mean_symbol_energy'] for r in group]))))
    scored=[r for r in group if r['aligned']]
    for baseline in ['sign','pair']:
      delta=np.array([(r['metrics']['sequence']['payload_errors']-r['metrics'][baseline]['payload_errors'])/304 for r in scored])
      frames=[(r['metrics'][baseline]['packet_pass'],r['metrics']['sequence']['packet_pass']) for r in group]
      mean=float(delta.mean()) if len(delta) else None;se=float(delta.std(ddof=1)/math.sqrt(len(delta))) if len(delta)>1 else None
      informative=len(delta)>1 and np.any(delta)
      paired.append(dict(stage=stage,pattern=pattern,profile=profile,ebn0_db=eb,baseline=baseline,trials=len(group),aligned=len(scored),
        baseline_errors=sum(r['metrics'][baseline]['payload_errors'] for r in scored),sequence_errors=sum(r['metrics']['sequence']['payload_errors'] for r in scored),
        paired_ber_change=mean,change95_low=mean-1.96*se if informative else None,change95_high=mean+1.96*se if informative else None,
        interval_note='Paired trial-block normal approximation' if informative else 'No nonzero trial differences or insufficient acquired trials; no zero-width interval',
        packet_recovered=sum(not a and b for a,b in frames),packet_regressed=sum(a and not b for a,b in frames)))
 table(stage+'-summary.csv',summary);table(stage+'-paired.csv',paired)
 (HERE/(stage+'-validation.json')).write_text(json.dumps(dict(trial_count=len(rows),all_transmitted_payloads_known=True,all_returned_decisions_recounted=True,frozen_hashes_match=freeze_check()==json.loads((HERE/'frozen-hashes.json').read_text())),indent=2)+'\n')
 print('validated',stage,len(rows))
if __name__=='__main__':main(sys.argv[1])
