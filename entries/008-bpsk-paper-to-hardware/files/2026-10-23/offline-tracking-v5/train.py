"""Training only: libre01 and new synthetic realizations. No held-out inputs."""
from pathlib import Path
import sys,json,importlib.util,hashlib,time
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'offline-ber'))
from diagnostic import frame,freeze,score_bits
import receiver as r
MODEL=json.loads((HERE/'model.json').read_text());ALPHAS=[0.,.02,.04,.06,.1,.25,.5]
# New seeds, patterns and channel realizations; independent of legacy stress suite.
PROFILES=['static','offset72','offset144','ramp60','ramp140','walk6','walk15']
def synthetic(pattern,profile,eb,trial,full=False):
    rng=np.random.default_rng(np.random.SeedSequence([934551,int(full),pattern,PROFILES.index(profile),eb,trial]))
    k=np.arange(304);data=(rng.integers(0,2,304) if pattern==0 else (k//16)%2 if pattern==1 else (k%32==31)).astype(np.uint8)
    truth=np.unpackbits(np.frombuffer(frame(np.packbits(data).tobytes(),int(rng.integers(2**32))),np.uint8));states=np.cumsum(truth)%2
    mu=r.centers(MODEL);mu/=np.sqrt(np.mean(abs(mu)**2));t=np.arange(808*40)/48000
    direction=int(rng.choice([-1,1]));f=float(rng.uniform(-8000,8000)) if full else 0.
    phase=rng.uniform(-np.pi,np.pi)+2*np.pi*f*t
    if profile.startswith('offset'):phase+=2*np.pi*direction*float(profile[6:])*t
    if profile.startswith('ramp'):phase+=np.pi*direction*float(profile[4:])*t*t
    if profile.startswith('walk'):phase+=np.cumsum(rng.normal(0,np.deg2rad(float(profile[4:]))/np.sqrt(40),len(t)))
    n0=10**(-eb/10);gain=2**rng.uniform(-1,1);h=np.exp(1j*phase)
    if full:
        start=int(rng.integers(24000,120001));x=(rng.normal(size=192000)+1j*rng.normal(size=192000))*np.sqrt(n0/2)
        x[start:start+808*40]+=np.repeat(mu[states],40)*h/np.sqrt(40)
        return gain*x,truth,start
    z=mu[states]*h.reshape(808,40).mean(axis=1)+(rng.normal(size=808)+1j*rng.normal(size=808))*np.sqrt(n0/2)
    return gain*z,truth,None

def main():
    rows=[]
    for pattern in range(3):
      for profile in PROFILES:
       for eb in [8,12]:
        for trial in range(6):
         z,truth,_=synthetic(pattern,profile,eb,trial)
         old=r.v4.sequence_glrt(z,r.centers(MODEL),3)[0]
         row=dict(kind='synthetic_symbols',pattern=pattern,profile=profile,eb=eb,trial=trial,baseline_errors=int(np.sum(old[344:648]!=truth[344:648])),candidates={})
         for a in ALPHAS:
            bits,_=r.detect_symbols(z,MODEL,a);row['candidates'][str(a)]=int(np.sum(bits[344:648]!=truth[344:648]))
         rows.append(row)
    # Full acquisition training includes the new dynamic channels, unknown start/CFO.
    for pattern in range(3):
      for profile in PROFILES:
       for eb in [8,12]:
        x,truth,start=synthetic(pattern,profile,eb,70,True);res=r.locate(x,MODEL)
        aligned=res['detected'] and abs(res['start_sample']-start)<=20
        row=dict(kind='synthetic_full',pattern=pattern,profile=profile,eb=eb,aligned=bool(aligned),timing_error=res.get('start_sample',-999999)-start,candidates={})
        if aligned:
            z=r.v4.symbols_at(x,res)
            for a in ALPHAS:row['candidates'][str(a)]=int(np.sum(r.detect_symbols(z,MODEL,a)[0][344:648]!=truth[344:648]))
        rows.append(row)
    source=json.loads((ROOT/'offline-sequence-v4/training-source.json').read_text())
    # training-source can contain a wrapper; inspect/handle the isolated source only.
    if 'source' in source:source=source['source']
    x=np.load(ROOT/'offline-ber/libre01-48k.npz')['iq'];ref=freeze(x,source)
    for eb in ['clean',8,12]:
      for trial in range(1 if eb=='clean' else 12):
        rng=np.random.default_rng(945000+(0 if eb=='clean' else eb*100)+trial)
        shift=0 if eb=='clean' else int(rng.integers(-40000,40001));f=0 if eb=='clean' else float(rng.uniform(-1500,1500))
        if eb=='clean':obs=x
        else:
            signal=np.roll(ref['normalized_iq'],shift)*np.exp(1j*(rng.uniform(-np.pi,np.pi)+2*np.pi*f*np.arange(len(x))/48000))
            obs=2**rng.uniform(-1,1)*(signal+(rng.normal(size=len(x))+1j*rng.normal(size=len(x)))*np.sqrt(10**(-eb/10)/2))
        res=r.locate(obs,MODEL);aligned=res['detected'] and abs(res['start_sample']-ref['start_sample']-shift)<=20
        row=dict(kind='libre01',eb=eb,trial=trial,aligned=bool(aligned),candidates={})
        if aligned:
            z=r.v4.symbols_at(obs,res)
            for a in ALPHAS:row['candidates'][str(a)]=score_bits(r.detect_symbols(z,MODEL,a)[0],ref['expected_bits'])['bit_errors']
        rows.append(row)
    totals={str(a):sum(row['candidates'].get(str(a),0) for row in rows) for a in ALPHAS}
    # Select lowest total known-bit errors; fixed order breaks ties toward less tracking.
    selected=min(ALPHAS,key=lambda a:totals[str(a)])
    result=dict(training_seed=934551,libre_noise_seed_base=945000,alphas=ALPHAS,criterion='Minimize total training known-bit errors on aligned trials, including preamble-only alpha=0; no payload priors. Acquisition misses independent of alpha.',error_totals=totals,selected_alpha=selected,rows=rows)
    (HERE/'training.json').write_text(json.dumps(result,indent=2)+'\n')
    MODEL['tracking_alpha']=selected;(HERE/'model.json').write_text(json.dumps(MODEL,indent=2)+'\n')
    print(json.dumps(dict(totals=totals,selected=selected,alignment={kind:[sum(row.get('aligned',False) for row in rows if row['kind']==kind),sum(row['kind']==kind for row in rows)] for kind in ['synthetic_full','libre01']})),flush=True)
if __name__=='__main__':main()
