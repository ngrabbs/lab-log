"""Training-only bounded window comparison. Opens libre01 IQ only.
All candidate decisions share the same acquisition and observed symbols.
"""
import json,sys,hashlib,csv
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'offline-ber'
sys.path.insert(0,str(OLD))
from diagnostic import freeze,score_bits,crc_observation,SCORE
from receiver import pair,sequence_glrt,symbols_at
WINDOWS=[3,5,7]
def main():
    model=json.loads((HERE/'model.json').read_text());source=json.loads((HERE/'training-source.json').read_text())
    assert source['name']=='libre01';path=OLD/source['filename']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source['npz_sha256']
    ref=freeze(np.load(path)['iq'],source);mu=np.array([complex(*v) for v in model['centers']])
    ledger=[];(HERE/'training-trials.jsonl').write_text('')
    def record(iq,kind,shift=0,delta=0,**extra):
        result=pair.acquire(iq,model);z=symbols_at(iq,result) if result['detected'] else None
        for version,window in [('v3',None)]+[(f'L{w}',w) for w in WINDOWS]:
            bits=result.get('bits') if window is None or z is None else sequence_glrt(z,mu,window)[0]
            row=dict(version=version,kind=kind,**extra,detected=result['detected'],metric=result.get('metric'),
                     start_sample=result.get('start_sample'),cfo_hz=result.get('cfo_hz'))
            if kind!='noise':
                row['aligned']=result['detected'] and abs(result['start_sample']-(ref['start_sample']+shift))<=20
            if bits is not None:
                row['decisions_hex']=np.packbits(np.maximum(bits,0).astype(np.uint8)).tobytes().hex()
                sync_errors=int(np.sum(bits[256:288]!=ref['expected_bits'][256:288]))
                row['sync_errors']=sync_errors
                row['bit_errors']=score_bits(bits,ref['expected_bits'])['bit_errors']
                row['false_changes']=int(np.sum(bits[SCORE[ref['expected_bits'][SCORE]==0]]!=0))
                row['missed_changes']=int(np.sum(bits[SCORE[ref['expected_bits'][SCORE]==1]]!=1))
                row['frame_pass']=sync_errors==0 and crc_observation(bits)
            ledger.append(row)
            with (HERE/'training-trials.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    record(ref['normalized_iq'],'clean')
    for eb in [8,12]:
      for seed in [66001,66002,66003]:
        rng=np.random.default_rng(seed+1000*eb)
        for trial in range(10):
            shift=int(rng.integers(-40000,40001));delta=float(rng.uniform(-1500,1500))
            phase=float(rng.uniform(-np.pi,np.pi));gain=float(2**rng.uniform(-1,1))
            signal=np.roll(ref['normalized_iq'],shift)*np.exp(1j*(phase+2*np.pi*delta*np.arange(192000)/48000))
            noise=(rng.normal(size=192000)+1j*rng.normal(size=192000))*np.sqrt(10**(-eb/10)/2)
            record(gain*(signal+noise),'noisy',shift,delta,ebn0_db=eb,seed=seed,trial=trial)
      print('training point complete',eb,flush=True)
    for trial in range(30):
        rng=np.random.default_rng(870000+trial)
        record((rng.normal(size=192000)+1j*rng.normal(size=192000))/np.sqrt(2),'noise',trial=trial)
    summary=[]
    for version in ['v3']+[f'L{w}' for w in WINDOWS]:
      for point in ['clean','8','12','noise']:
        group=[r for r in ledger if r['version']==version and (r['kind']==point or (r['kind']=='noisy' and str(r['ebn0_db'])==point))]
        aligned=[r for r in group if r.get('aligned',False)]
        summary.append(dict(version=version,point=point,trials=len(group),detected=sum(r['detected'] for r in group),
          aligned=len(aligned),frames=sum(r.get('frame_pass',False) for r in group),aligned_bits=len(aligned)*184,
          aligned_errors=sum(r['bit_errors'] for r in aligned),false_changes=sum(r['false_changes'] for r in aligned),
          missed_changes=sum(r['missed_changes'] for r in aligned)))
    with (HERE/'training-summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
