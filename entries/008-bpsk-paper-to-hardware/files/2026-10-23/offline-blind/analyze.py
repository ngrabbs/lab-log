"""Recompute counts, trial-based intervals and decision-ledger validation."""
import json,csv,math,sys,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'offline-ber'
sys.path.insert(0,str(OLD))
from diagnostic import frame_reference,score_bits,crc_observation,cluster_interval

def wilson(k,n):
    z=1.95996398454;p=k/n;d=1+z*z/n
    c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h),min(1,c+h)
rows=[json.loads(x) for x in (HERE/'trials.jsonl').read_text().splitlines()]
manifest=json.loads((OLD/'manifest.json').read_text());sources={s['name']:s for s in manifest['sources']}
for r in rows:
    if r['capture'] not in sources or not r['detected']:continue
    s=sources[r['capture']];expected,_=frame_reference(s['native_hex'],s['rf_sequence'])
    bits=np.unpackbits(np.frombuffer(bytes.fromhex(r['decisions_hex']),np.uint8));bits=bits.astype(np.int8);bits[0]=-1
    assert score_bits(bits,expected)['bit_errors']==r['candidate_preamble_errors']
    assert crc_observation(bits)==r['outer_crc32_pass']
    assert int(np.sum(bits[288:680]!=expected[288:680]))==r['body_replay_reference_errors']
intervals=[]
for name in ['libre02','pluto00','pluto20']:
 for eb in [8,12]:
    group=[r for r in rows if r['capture']==name and r.get('ebn0_db')==eb]
    aligned=[r for r in group if r['aligned_within_half_symbol']]
    ber,lo,hi,method=cluster_interval([r['bit_errors'] for r in aligned],184)
    a=sum(r['aligned_within_half_symbol'] for r in group);f=sum(r['frame_pass'] for r in group)
    intervals.append(dict(capture=name,ebn0_db=eb,aligned=a,trials=len(group),
        aligned_wilson95_low=wilson(a,len(group))[0],aligned_wilson95_high=wilson(a,len(group))[1],
        frames=f,frame_wilson95_low=wilson(f,len(group))[0],frame_wilson95_high=wilson(f,len(group))[1],
        conditional_ber=ber,ber95_low=lo,ber95_high=hi,ber_interval_method=method))
with (HERE/'intervals.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(intervals[0]));w.writeheader();w.writerows(intervals)
assert len(rows)==214
assert all(0<=r.get('metric',0)<=1.000001 for r in rows)
negative=[r for r in rows if r['kind']=='negative']
report=dict(total_trials=len(rows),held_out_clean=3,noisy_held_out=180,training_clean=1,
    noise_only_windows=len(negative),noise_false_candidates=sum(r['detected'] for r in negative),
    false_candidate_one_sided95_upper=1-.05**(1/len(negative)),
    all_detected_decisions_recounted=True,all_metrics_in_unit_interval=True,
    model_and_receiver_hashes_unchanged=json.loads((HERE/'lock.json').read_text())=={
      f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['model.json','receiver.py']})
assert report['model_and_receiver_hashes_unchanged']
(HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
