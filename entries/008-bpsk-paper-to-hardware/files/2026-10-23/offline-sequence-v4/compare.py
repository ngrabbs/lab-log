"""Paired detector comparison on identical IQ/acquisition; BER uses trial blocks."""
import json,csv,math,sys,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'offline-geometry-v3';OLD=HERE.parent/'offline-ber'
sys.path.insert(0,str(OLD))
from diagnostic import frame_reference,SCORE,score_bits,crc_observation
old=[json.loads(x) for x in (BASE/'trials.jsonl').read_text().splitlines()]
new=[json.loads(x) for x in (HERE/'trials.jsonl').read_text().splitlines()]
def key(r):return r['capture'],r['kind'],r.get('ebn0_db'),r.get('seed'),r.get('trial')
a={key(r):r for r in old};b={key(r):r for r in new};assert a.keys()==b.keys()
def bits(r):
 v=np.unpackbits(np.frombuffer(bytes.fromhex(r['decisions_hex']),np.uint8)).astype(np.int8);v[0]=-1;return v
sources={s['name']:s for s in json.loads((OLD/'manifest.json').read_text())['sources']}
truth={name:frame_reference(s['native_hex'],s['rf_sequence'])[0] for name,s in sources.items()}
for k,r in a.items():
 s=b[k]
 for field in ['input_iq_sha256','detected','start_sample','cfo_hz','metric','coarse_metric','block_metrics','aligned_within_half_symbol','scored_bits']:
    assert r.get(field)==s.get(field),(k,field)
 if r['detected']:
    assert r['decisions_hex']==s['baseline_decisions_hex']
    assert r['sync_errors']==s['baseline_sync_errors']
 if r['kind'] not in ['negative'] and r['detected']:
    for item in [r,s]:
      d=bits(item);expected=truth[item['capture']]
      assert score_bits(d,expected)['bit_errors']==item['candidate_preamble_errors']
      assert crc_observation(d)==item['outer_crc32_pass']
      sync=int(np.sum(d[256:288]!=expected[256:288]));assert sync==item['sync_errors']
      assert (sync==0 and crc_observation(d))==item['frame_pass']
rows=[];classes=[]
for name in ['libre02','pluto00','pluto20','ALL']:
 for eb in [8,12,'ALL']:
    keys=[k for k in a if k[1]=='noisy' and (name=='ALL' or k[0]==name) and (eb=='ALL' or k[2]==eb)]
    aligned=[k for k in keys if a[k]['aligned_within_half_symbol']]
    n=len(aligned)*184;ea=sum(a[k]['bit_errors'] for k in aligned);en=sum(b[k]['bit_errors'] for k in aligned)
    delta=np.array([(b[k]['bit_errors']-a[k]['bit_errors'])/184 for k in aligned])
    mean=float(delta.mean());se=float(delta.std(ddof=1)/np.sqrt(len(delta)))
    fixes=regressions=0
    for k in aligned:
       expected=truth[k[0]][SCORE];x=bits(a[k])[SCORE]!=expected;y=bits(b[k])[SCORE]!=expected
       fixes+=int(np.sum(x&~y));regressions+=int(np.sum(~x&y))
    oldframes=sum(a[k].get('frame_pass',False) for k in keys);newframes=sum(b[k].get('frame_pass',False) for k in keys)
    rows.append(dict(capture=name,ebn0_db=eb,trials=len(keys),aligned=len(aligned),scored_bits=n,
      v3_errors=ea,v4_errors=en,v3_ber=ea/n,v4_ber=en/n,ber_ratio_v4_v3=en/ea if ea else None,
      paired_ber_change=mean,paired_change95_low=mean-1.96*se if np.any(delta) else None,paired_change95_high=mean+1.96*se if np.any(delta) else None,
      interval_note="95% paired trial-block normal approximation" if np.any(delta) else "No observed trial differences: normal interval unavailable; zero counts do not establish equal true BER",
      bit_errors_fixed=fixes,bit_errors_introduced=regressions,
      v3_frames=oldframes,v4_frames=newframes,
      frames_recovered=sum(not a[k].get('frame_pass',False) and b[k].get('frame_pass',False) for k in keys),
      frames_regressed=sum(a[k].get('frame_pass',False) and not b[k].get('frame_pass',False) for k in keys)))
    for label in [0,1]:
       counts=[0,0,0]
       for k in aligned:
          idx=SCORE[truth[k[0]][SCORE]==label];counts[0]+=len(idx)
          counts[1]+=int(np.sum(bits(a[k])[idx]!=label));counts[2]+=int(np.sum(bits(b[k])[idx]!=label))
       classes.append(dict(capture=name,ebn0_db=eb,transmitted_bit=label,scored_bits=counts[0],v3_errors=counts[1],v4_errors=counts[2],v3_ber=counts[1]/counts[0],v4_ber=counts[2]/counts[0]))
for filename,records in [('paired-summary.csv',rows),('bit-class-summary.csv',classes)]:
 with (HERE/filename).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
report=dict(paired_trial_count=len(a),exact_input_iq_hashes_match=True,all_acquisition_outputs_identical=True,
 baseline_decision_bytes_reproduced_exactly=True,paired_ber_intervals='95% normal approximation over paired trial BER differences, conditional on aligned trials and fixed RF waveforms; sparse tails are descriptive.',
 baseline_ledger_sha256=hashlib.sha256((BASE/'trials.jsonl').read_bytes()).hexdigest())
(HERE/'paired-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([r for r in rows if r['capture']=='ALL'],indent=2))
