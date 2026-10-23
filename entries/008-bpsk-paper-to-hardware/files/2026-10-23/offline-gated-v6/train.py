"""Fresh training realizations only; never opens held-out captures/stress ledgers."""
from pathlib import Path
import sys,json,itertools,hashlib
import numpy as np
import receiver as r
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'offline-ber'))
from diagnostic import frame,freeze
MODEL=json.loads((HERE/'model.json').read_text());PROTOCOL=json.loads((HERE/'protocol.json').read_text())
PROFILES=['static','offset84','offset156','ramp8','ramp80','ramp160','walk5','walk18']
CANDIDATES=[dict(gate_drift_score=d,gate_min_drift_hz_s=m,gate_decision_gap=g) for d,m,g in itertools.product(PROTOCOL['candidate_drift_scores'],PROTOCOL['candidate_min_drift_hz_s'],PROTOCOL['candidate_decision_gaps'])]

def synthetic(pattern,profile,eb,trial,full=False):
    rng=np.random.default_rng(np.random.SeedSequence([PROTOCOL['training_seed'],int(full),pattern,PROFILES.index(profile),0 if eb=='clean' else eb,trial]))
    k=np.arange(304);data=(rng.integers(0,2,304) if pattern==0 else (k//24)%2 if pattern==1 else k%48==47).astype(np.uint8)
    truth=np.unpackbits(np.frombuffer(frame(np.packbits(data).tobytes(),int(rng.integers(2**32))),np.uint8));states=np.cumsum(truth)%2
    mu=r.centers(MODEL);mu/=np.sqrt(np.mean(abs(mu)**2));t=np.arange(808*40)/48000
    direction=int(rng.choice([-1,1]));f=float(rng.uniform(-8000,8000)) if full else 0.
    angle=rng.uniform(-np.pi,np.pi)+2*np.pi*f*t
    if profile.startswith('offset'):angle+=2*np.pi*direction*float(profile[6:])*t
    if profile.startswith('ramp'):angle+=np.pi*direction*float(profile[4:])*t*t
    if profile.startswith('walk'):angle+=np.cumsum(rng.normal(0,np.deg2rad(float(profile[4:]))/np.sqrt(40),len(t)))
    n0=0. if eb=='clean' else 10**(-eb/10);gain=2**rng.uniform(-1,1);h=np.exp(1j*angle)
    if full:
        start=int(rng.integers(24000,120001));x=(rng.normal(size=192000)+1j*rng.normal(size=192000))*np.sqrt(n0/2)
        x[start:start+808*40]+=np.repeat(mu[states],40)*h/np.sqrt(40)
        return gain*x,truth,start
    z=mu[states]*h.reshape(808,40).mean(axis=1)+(rng.normal(size=808)+1j*rng.normal(size=808))*np.sqrt(n0/2)
    return gain*z,truth,None

def main():
    rows=[]
    def evaluate(z,truth,ix,meta):
        prepared=r.prepare(z,MODEL);base=r.v5.detect_symbols(z,MODEL,0.)[0];cont=r.v5.detect_symbols(z,MODEL,.06)[0]
        row=dict(**meta,input_symbols_sha256=hashlib.sha256(np.ascontiguousarray(z).tobytes()).hexdigest(),scored_bits=len(ix),
            preamble_only_errors=int(np.sum(base[ix]!=truth[ix])),continuous_errors=int(np.sum(cont[ix]!=truth[ix])),
            pilot=prepared[3],candidates=[])
        for c in CANDIDATES:
            bits,info=r.gated_prepared(prepared,dict(MODEL,**c))
            row['candidates'].append(dict(errors=int(np.sum(bits[ix]!=truth[ix])),enabled=info['tracking_enabled'],accepted_updates=info['accepted_updates']))
        rows.append(row)
    for pattern in range(3):
      for profile in PROFILES:
       for eb in [4,8,12]:
        for trial in range(3):
         z,truth,_=synthetic(pattern,profile,eb,trial)
         evaluate(z,truth,np.arange(344,648),dict(kind='synthetic_symbols',pattern=pattern,profile=profile,eb=eb,trial=trial))
    for pattern in range(3):
      for profile in ['static','ramp8','ramp80','ramp160','walk18']:
       for eb in [4,8,12,'clean']:
        x,truth,start=synthetic(pattern,profile,eb,40,True);res=r.locate(x,MODEL)
        aligned=res['detected'] and abs(res['start_sample']-start)<=20
        if not aligned:
            rows.append(dict(kind='synthetic_full',pattern=pattern,profile=profile,eb=eb,trial=40,aligned=False,acquisition=res));continue
        evaluate(r.v4.symbols_at(x,res),truth,np.arange(344,648),dict(kind='synthetic_full',pattern=pattern,profile=profile,eb=eb,trial=40,aligned=True,timing_error_samples=res['start_sample']-start))
    source=json.loads((ROOT/'offline-sequence-v4/training-source.json').read_text());assert source['name']=='libre01'
    p=ROOT/'offline-ber/libre01-48k.npz';assert hashlib.sha256(p.read_bytes()).hexdigest()==source['npz_sha256']
    x=np.load(p)['iq'];ref=freeze(x,source)
    for eb in ['clean',4,8,12]:
      for trial in range(1 if eb=='clean' else 16):
        rng=np.random.default_rng(PROTOCOL['libre01_noise_seed_base']+(0 if eb=='clean' else eb*100)+trial)
        shift=0 if eb=='clean' else int(rng.integers(-40000,40001));f=0 if eb=='clean' else float(rng.uniform(-1500,1500))
        if eb=='clean':obs=x
        else:
            signal=np.roll(ref['normalized_iq'],shift)*np.exp(1j*(rng.uniform(-np.pi,np.pi)+2*np.pi*f*np.arange(len(x))/48000))
            obs=2**rng.uniform(-1,1)*(signal+(rng.normal(size=len(x))+1j*rng.normal(size=len(x)))*np.sqrt(10**(-eb/10)/2))
        res=r.locate(obs,MODEL);aligned=res['detected'] and abs(res['start_sample']-ref['start_sample']-shift)<=20
        if not aligned:rows.append(dict(kind='libre01',eb=eb,trial=trial,aligned=False,acquisition=res));continue
        evaluate(r.v4.symbols_at(obs,res),ref['expected_bits'],np.arange(68,224),dict(kind='libre01',profile='capture',eb=eb,trial=trial,aligned=True))
    eligible=[];totals=[]
    scored=[row for row in rows if 'candidates' in row]
    for i,c in enumerate(CANDIDATES):
        regressions=sum(row['candidates'][i]['errors']>row['preamble_only_errors'] for row in scored if row['kind']=='libre01' or row['profile']=='static')
        total=sum(row['candidates'][i]['errors'] for row in scored)
        totals.append(dict(**c,total_errors=total,protected_trial_regressions=regressions,enabled=sum(row['candidates'][i]['enabled'] for row in scored)))
        if not regressions:eligible.append(i)
    assert eligible,'No eligible gate: predeclared fallback must be implemented before any held-out evaluation'
    selected=min(eligible,key=lambda i:(totals[i]['total_errors'],-CANDIDATES[i]['gate_drift_score'],-CANDIDATES[i]['gate_min_drift_hz_s'],-CANDIDATES[i]['gate_decision_gap']))
    MODEL.update(CANDIDATES[selected]);(HERE/'model.json').write_text(json.dumps(MODEL,indent=2)+'\n')
    result=dict(protocol=PROTOCOL,candidate_totals=totals,selected_candidate=selected,selected=CANDIDATES[selected],
        preamble_only_total_errors=sum(row['preamble_only_errors'] for row in scored),continuous_total_errors=sum(row['continuous_errors'] for row in scored),rows=rows)
    (HERE/'training.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(selected=totals[selected],preamble_only=result['preamble_only_total_errors'],continuous=result['continuous_total_errors'],cases=len(rows),aligned=sum(row.get('aligned',True) for row in rows),totals=totals)),flush=True)
if __name__=='__main__':main()
