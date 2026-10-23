"""Development comparison: opens libre01 IQ only, plus synthetic Gaussian noise.
No held-out IQ is loaded. Versions/parameters fixed before evaluation.
"""
import json,sys,hashlib,importlib.util,csv,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'offline-ber';BASE=HERE.parent/'offline-blind'
sys.path.insert(0,str(OLD))
from diagnostic import freeze,score_bits,crc_observation
from receiver import acquire
spec=importlib.util.spec_from_file_location('baseline',BASE/'receiver.py');baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
def main():
    model=json.loads((HERE/'model.json').read_text())
    source=json.loads((HERE/'training-source.json').read_text())
    assert source['name']=='libre01'
    path=OLD/source['filename'];assert hashlib.sha256(path.read_bytes()).hexdigest()==source['npz_sha256']
    ref=freeze(np.load(path)['iq'],source)
    ledger=[]
    (HERE/'training-trials.jsonl').write_text('')
    def record(iq,kind,shift=0,delta=0,**extra):
        for name,decoder in [('v1',baseline.acquire),('v2',acquire)]:
            r=decoder(iq,model);bits=r.pop('bits',None)
            row=dict(version=name,kind=kind,**extra,**r)
            if bits is not None:
                row['decisions_hex']=np.packbits(np.maximum(bits,0).astype(np.uint8)).tobytes().hex()
            if kind!='noise':
                row['timing_error_samples']=r.get('start_sample',-999999)-(ref['start_sample']+shift)
                row['aligned']=r['detected'] and abs(row['timing_error_samples'])<=20
                if bits is not None:
                    row['bit_errors']=score_bits(bits,ref['expected_bits'])['bit_errors']
                    row['cfo_error_hz']=r['cfo_hz']-(ref['cfo_hz']+delta)
                    row['frame_pass']=r['sync_errors']==0 and crc_observation(bits)
            ledger.append(row)
            with (HERE/'training-trials.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    record(ref['normalized_iq'],'clean')
    for eb in [8,12]:
      for seed in [44001,44002,44003]:
        rng=np.random.default_rng(seed+1000*eb)
        for trial in range(10):
            shift=int(rng.integers(-40000,40001));delta=float(rng.uniform(-1500,1500))
            phase=float(rng.uniform(-np.pi,np.pi));gain=float(2**rng.uniform(-1,1))
            signal=np.roll(ref['normalized_iq'],shift)*np.exp(1j*(phase+2*np.pi*delta*np.arange(192000)/48000))
            noise=(rng.normal(size=192000)+1j*rng.normal(size=192000))*np.sqrt(10**(-eb/10)/2)
            record(gain*(signal+noise),'noisy',shift,delta,ebn0_db=eb,seed=seed,trial=trial)
      print('training point complete',eb,flush=True)
    for trial in range(30):
        rng=np.random.default_rng(850000+trial)
        noise=(rng.normal(size=192000)+1j*rng.normal(size=192000))/np.sqrt(2)
        record(noise,'noise',trial=trial)
    summary=[]
    for name in ['v1','v2']:
      for kind in ['clean','8','12','noise']:
        group=[r for r in ledger if r['version']==name and (r['kind']==kind or (r['kind']=='noisy' and str(r['ebn0_db'])==kind))]
        aligned=[r for r in group if r.get('aligned')]
        summary.append(dict(version=name,point=kind,trials=len(group),detected=sum(r['detected'] for r in group),
          aligned=sum(r.get('aligned',False) for r in group),frames=sum(r.get('frame_pass',False) for r in group),
          aligned_bits=len(aligned)*184,aligned_errors=sum(r.get('bit_errors',0) for r in aligned)))
    with (HERE/'training-summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
