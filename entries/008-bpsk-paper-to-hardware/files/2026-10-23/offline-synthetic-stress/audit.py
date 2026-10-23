"""Validate frozen sources, all ledgers/summary counts and paper references."""
import csv,gzip,json,math,hashlib
from pathlib import Path
import numpy as np
from model_test import *

def main():
 assert freeze_check()==json.loads((HERE/'frozen-hashes.json').read_text())
 reports={}
 for stage,n in [('detector',3240),('full',570)]:
    rows=[json.loads(s) for s in gzip.open(HERE/(stage+'-trials.jsonl.gz'),'rt')];assert len(rows)==n
    summary=list(csv.DictReader((HERE/(stage+'-summary.csv')).open()))
    for r in summary:
      group=[x for x in rows if (r['pattern']=='ALL' or x['pattern']==r['pattern']) and x['profile']==r['profile'] and str(x['ebn0_db'])==r['ebn0_db']]
      scored=[x for x in group if x['metrics'][r['detector']]['scored_bits']];m=[x['metrics'][r['detector']] for x in scored]
      assert len(group)==int(r['trials']) and len(scored)==int(r['aligned'])
      assert sum(x['payload_errors'] for x in m)==int(r['payload_errors'])
      assert len(scored)*304==int(r['payload_bits'])
      assert sum(x['metrics'][r['detector']]['packet_pass'] for x in group)==int(r['packets'])
      for value in r.values():assert value.lower() not in ['nan','inf','-inf']
    # Exact synthetic input reproduction on every full IQ case. No detector rerun.
    if stage=='full':
      for row in rows:
        meta,truth,_,_,_=make_case(row['pattern'],row['profile'],row['ebn0_db'],row['seed'],'full',row['trial'])
        assert meta['input_iq_sha256']==row['input_iq_sha256']
      failures=sum(not r['aligned'] for r in rows);noisy=[r for r in rows if r['ebn0_db']!='clean']
      reports['full_alignment']=dict(all_aligned=len(rows)-failures,total=len(rows),
           noisy_aligned=sum(r['aligned'] for r in noisy),noisy_trials=len(noisy),
           clean_wrong_starts=sum(not r['aligned'] for r in rows if r['ebn0_db']=='clean'))
    reports[stage+'_trial_count']=n
 controls=list(csv.DictReader((HERE/'paper-control.csv').open()));measurable=0
 for row in controls:
    theory=float(row['theory_discrete_ns8']);observed=float(row['ber']);se=float(row['trial_ber_standard_error'])
    if theory*int(row['bits'])>=10:
      assert abs(observed-theory)<4*se,(row['detector'],row['ebn0_db'],row['nu']);measurable+=1
 reports.update(frozen_hashes_match=True,all_summary_counts_reconciled=True,
   all_full_iq_hashes_reproduced=True,paper_control_rows=len(controls),paper_measurable_rows_within_four_trial_standard_errors=measurable,
   paper_tail_note='12 dB controls have too few expected errors for a measured-tail validation; zero counts are not zero BER.')
 # Prior published local baseline assets remain unchanged; no edits to sources/results.
 for directory in ['offline-blind','offline-start-v2','offline-geometry-v3','offline-sequence-v4']:
    base=HERE.parent/directory;manifest=json.loads((base/'publication.json').read_text())
    for f in manifest['files']:assert hashlib.sha256((base/f['path']).read_bytes()).hexdigest()==f['sha256']
 reports['all_prior_result_hashes_unchanged']=True
 (HERE/'audit.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
