"""Offline evaluation harness. Truth/normalization stay outside acquire(iq, model)."""
import sys,json,hashlib,time,csv
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'offline-ber'
sys.path.insert(0,str(OLD))
from diagnostic import freeze,score_bits,crc_observation
from receiver import acquire

def main():
    model=json.loads((HERE/'model.json').read_text())
    manifest=json.loads((OLD/'manifest.json').read_text())
    # Hash receiver/config before any held-out calls. Source/config are not tuned
    # after running held-out trials. Raw inputs retain their existing hashes.
    lock={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['model.json','receiver.py']}
    (HERE/'lock.json').write_text(json.dumps(lock,indent=2)+'\n')
    rows=[]
    def evaluate(x,tag,ref=None,shift=0,cfo_shift=0,**extra):
        begin=time.monotonic();result=acquire(x,model)
        bits=result.pop('bits',None)
        if bits is not None:
            result['decisions_hex']=np.packbits(np.maximum(bits,0).astype(np.uint8)).tobytes().hex()
            result['unobserved_bit_indices']=[0]
        row=dict(capture=tag,**extra,**result,elapsed_seconds=time.monotonic()-begin)
        if ref is not None:
            start=ref['start_sample']+shift
            row.update(true_start_sample=start,true_cfo_hz=ref['cfo_hz']+cfo_shift)
            aligned=bool(result['detected'] and abs(result['start_sample']-start)<=20)
            row['aligned_within_half_symbol']=aligned
            if result['detected']:
                row['timing_error_samples']=result['start_sample']-start
                row['cfo_error_hz']=result['cfo_hz']-row['true_cfo_hz']
                # Wrong-candidate errors are retained separately, never accepted
                # as aligned BER on the periodic preamble alone.
                row['candidate_preamble_errors']=score_bits(bits,ref['expected_bits'])['bit_errors']
                row['outer_crc32_pass']=crc_observation(bits,ref['native_bytes'])
                row['body_replay_reference_errors']=int(np.sum(bits[288:680]!=ref['expected_bits'][288:680]))
                row['frame_pass']=result['sync_errors']==0 and row['outer_crc32_pass']
            row['scored_bits']=184 if aligned else 0
            row['bit_errors']=row.get('candidate_preamble_errors') if aligned else None
        rows.append(row)
        with (HERE/'trials.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
        return row
    (HERE/'trials.jsonl').write_text('')
    # Training check and negatives, before held-out calls; no threshold adjustment.
    s=manifest['sources'][0];x=np.load(OLD/s['filename'])['iq'];r=freeze(x,s)
    print('training',evaluate(x,'libre01',r,kind='training'),flush=True)
    for i in range(30):
        rng=np.random.default_rng(900000+i)
        x=(rng.normal(size=192000)+1j*rng.normal(size=192000))/np.sqrt(2)
        evaluate(x,'noise_only',kind='negative',trial=i)
    print('negatives',sum(r['detected'] for r in rows if r['kind']=='negative'),flush=True)
    for s in manifest['sources'][1:]:
        assert s['name'] in model['test_captures']
        p=OLD/s['filename'];assert hashlib.sha256(p.read_bytes()).hexdigest()==s['npz_sha256']
        x=np.load(p)['iq'];r=freeze(x,s) # Evaluation oracle only, not a receiver argument.
        print('clean',evaluate(x,s['name'],r,kind='clean'),flush=True)
        for eb in model['ebn0_db']:
            for seed in model['noise_seeds']:
                # Independent source/point streams, recorded for exact replay.
                rng=np.random.default_rng(seed+int(eb)*1000+manifest['sources'].index(s)*100000)
                for trial in range(model['trials_per_seed']):
                    shift=int(rng.integers(-40000,40001));delta=float(rng.uniform(-1500,1500))
                    phase=float(rng.uniform(-np.pi,np.pi));gain=float(2**rng.uniform(-1,1))
                    signal=np.roll(r['normalized_iq'],shift)
                    signal=signal*np.exp(1j*(phase+2*np.pi*delta*np.arange(len(signal))/48000))
                    noise=(rng.normal(size=len(signal))+1j*rng.normal(size=len(signal)))*np.sqrt(10**(-eb/10)/2)
                    evaluate(gain*(signal+noise),s['name'],r,shift,delta,
                             kind='noisy',ebn0_db=eb,seed=seed,trial=trial,
                             injected_delay_samples=shift,injected_cfo_hz=delta,
                             injected_phase_rad=phase,gain=gain)
            print('done',s['name'],eb,flush=True)
    groups=[]
    for name in model['test_captures']:
        for eb in ['clean']+model['ebn0_db']:
            selected=[r for r in rows if r['capture']==name and ((eb=='clean' and r['kind']=='clean') or (r['kind']=='noisy' and r['ebn0_db']==eb))]
            detected=[r for r in selected if r['detected']];aligned=[r for r in selected if r['aligned_within_half_symbol']]
            n=sum(r['scored_bits'] for r in selected);errors=sum(r['bit_errors'] or 0 for r in selected)
            groups.append(dict(capture=name,ebn0_db=eb,trials=len(selected),detections=len(detected),
                aligned=len(aligned),misses=sum(not r['detected'] for r in selected),
                wrong_start=sum(r['detected'] and not r['aligned_within_half_symbol'] for r in selected),
                sync_exact=sum(r.get('sync_errors',32)==0 for r in selected),
                frames=sum(r.get('frame_pass',False) for r in selected),scored_bits=n,
                bit_errors=errors,conditional_preamble_ber=errors/n if n else None,
                max_abs_aligned_cfo_error_hz=max([abs(r['cfo_error_hz']) for r in aligned],default=None)))
    with (HERE/'summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(groups[0]));w.writeheader();w.writerows(groups)
    assert lock=={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in lock}
    print(json.dumps(groups,indent=2),flush=True)
if __name__=='__main__':main()
