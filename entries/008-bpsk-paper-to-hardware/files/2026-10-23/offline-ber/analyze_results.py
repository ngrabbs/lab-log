"""Derive theory checks, bit-class errors and coarse BER thresholds from saved counts."""
from pathlib import Path
import argparse,csv,json,math,hashlib
import numpy as np
from diagnostic import SCORE

def rows(path):return list(csv.DictReader(path.open()))
def theory(eb,kind):
    g=10**(eb/10)
    return .5*math.erfc(math.sqrt(g)) if kind=='coherent' else .5*math.exp(-g)
def threshold(series,target=.001):
    points=sorted((float(r['ebn0_db']),float(r['ber'])) for r in series)
    for (x,y),(a,b) in zip(points,points[1:]):
        if y>=target>=b>0:
            return x+(math.log10(target)-math.log10(y))/(math.log10(b)-math.log10(y))*(a-x)
    return None

def main(out):
    fast=rows(out/'fast-summary.csv');checks=[]
    for kind,curve in [('coherent','ideal_coherent_random_phase'),('dbpsk','ideal_dbpsk_random_data'),('dbpsk','ideal180_known55_dbpsk_data')]:
        for r in fast:
            if r['curve']!=curve:continue
            eb=float(r['ebn0_db']);pred=theory(eb,kind);n=int(r['scored_bits']);observed=float(r['ber'])
            error=max((float(r['ci95_high'])-observed)/1.96,(observed-float(r['ci95_low']))/1.96)
            z=abs(observed-pred)/error if error>0 and int(r['bit_errors'])>0 else None
            checks.append(dict(curve=curve,ebn0_db=eb,theory=pred,measured=observed,expected_errors=pred*n,observed_errors=int(r['bit_errors']),cluster_z=z))
    bycurve={name:[r for r in fast if r['curve']==name] for name in {r['curve'] for r in fast}}
    thresholds={name:threshold(values) for name,values in bycurve.items()}
    ideal_dbpsk=10*math.log10(math.log(500));lo,hi=0.,20.
    for _ in range(100):
        mid=(lo+hi)/2
        if theory(mid,'coherent')>.001:lo=mid
        else:hi=mid
    phase=next(iter(json.loads((Path(__file__).resolve().parent/'manifest.json').read_text())['sources']))
    bits=np.unpackbits(np.frombuffer(bytes([0x55])*32,np.uint8))[SCORE]
    masks=np.load(out/'fast-error-masks.npz');transitions=[]
    np.savez_compressed(out/'fast-error-counts.npz',**{k:np.unpackbits(masks[k],axis=1).sum(axis=1).astype(np.int16) for k in masks.files})
    for name in ('ideal180_known55_dbpsk_data','ideal135_known55_dbpsk_data','libre01_frozen_dbpsk_data','libre02_frozen_dbpsk_data','pluto00_frozen_dbpsk_data','pluto20_frozen_dbpsk_data'):
        for eb in range(-4,13,2):
            keys=[k for k in masks.files if k.startswith(name+f'_e{eb}_s')]
            e=np.concatenate([np.unpackbits(masks[k],axis=1)[:,:len(SCORE)] for k in keys])
            for bit in (0,1):
                selected=e[:,bits==bit];transitions.append(dict(curve=name,ebn0_db=eb,known_bit=bit,meaning='phase_change' if bit else 'no_phase_change',scored_bits=selected.size,bit_errors=int(selected.sum()),ber=float(selected.mean())))
    with (out/'transition-ber.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(transitions[0]));w.writeheader();w.writerows(transitions)
    frozen=json.loads((out/'frozen-references.json').read_text());ratio=max(v['existing_matched_filter_noise_variance'] for v in frozen.values())/10**(-12/10)
    intervals=[]
    for filename in ('scheduled-summary.csv','template-summary.csv'):
        for r in rows(out/filename):
            n=int(r['scheduled_trials'])
            for metric,key in [('exact_sync','sync_exact_count'),('scheduled_sync_plus_crc32','scheduled_frame_pass_count')]:
                k=int(r[key]);p=k/n;z=1.96;denom=1+z*z/n
                center=(p+z*z/(2*n))/denom;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
                intervals.append(dict(method=filename.split('-')[0],capture=r['curve'],ebn0_db=r['ebn0_db'],observation=metric,successes=k,trials=n,fraction=p,ci95_low=max(0,center-half),ci95_high=min(1,center+half),interval='Wilson 95%, independent injected-noise trials conditional on fixed waveform'))
    with (out/'sync-frame-intervals.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(intervals[0]));w.writeheader();w.writerows(intervals)
    assets=[p for p in out.iterdir() if p.suffix in ('.csv','.npz') or p.name.endswith('.gz')]
    report=dict(theory_checks=checks,coarse_loglinear_thresholds_ber_1e_minus3_db=thresholds,ideal_dbpsk_theory_threshold_db=ideal_dbpsk,ideal_coherent_theory_threshold_db=(lo+hi)/2,coarse_excess_vs_ideal_dbpsk_db={k:v-ideal_dbpsk for k,v in thresholds.items() if v is not None and k.endswith('_frozen_dbpsk_data')},largest_original_noise_fraction_of_12db_target=ratio,method='Thresholds interpolate log BER on a 2 dB grid, not calibrated RF sensitivity or precise crossing measurements. Trial-block intervals are conditional on each fixed capture. Theory checks with <100 expected/observed errors do not validate the tail.',raw_and_summary_hashes=[dict(filename=p.name,size_bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(assets)])
    (out/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('theory_checks','raw_and_summary_hashes')},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);main(p.parse_args().output)
