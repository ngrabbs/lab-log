"""Synthetic independently known transport payloads; no radio/network access."""
from pathlib import Path
import importlib.util,json,sys,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'offline-sequence-v4';OLD=HERE.parent/'offline-ber'
sys.path.insert(0,str(OLD))
from diagnostic import frame,crc_observation
spec=importlib.util.spec_from_file_location('frozen_sequence_v4',BASE/'receiver.py')
v4=importlib.util.module_from_spec(spec);spec.loader.exec_module(v4)
MODEL=json.loads((BASE/'model.json').read_text())
MU=np.array([complex(*v) for v in MODEL['centers']]);MU/=np.sqrt(np.mean(abs(MU)**2))
PAYLOAD=np.arange(344,648);PREAMBLE=np.arange(68,252)
PATTERNS=['zeros','ones','alternating55','runs32','sparse_ones','random_iid']
PROFILES=['static','residual002','residual010','ramp100','walk3','walk12']
FULL_PROFILES=['static','ramp5','ramp100','walk3','walk12']
RATE=48000;SPS=40;N=808

def freeze_check():
    selection=json.loads((BASE/'selection.json').read_text());result={}
    for name,digest in selection['frozen_receiver_model'].items():
        p=BASE/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
        result['offline-sequence-v4/'+name]=digest
    for directory,key in [('offline-start-v2','acquisition_sha256'),('offline-geometry-v3','pair_detector_sha256')]:
        p=HERE.parent/directory/'receiver.py';assert hashlib.sha256(p.read_bytes()).hexdigest()==selection[key]
        result[directory+'/receiver.py']=selection[key]
    return result

def payload(pattern,rng):
    k=np.arange(304)
    if pattern=='zeros':return np.zeros(304,np.uint8)
    if pattern=='ones':return np.ones(304,np.uint8)
    if pattern=='alternating55':return (k%2).astype(np.uint8)
    if pattern=='runs32':return ((k//32)%2).astype(np.uint8)
    if pattern=='sparse_ones':return (k%64==63).astype(np.uint8)
    if pattern=='random_iid':return rng.integers(0,2,304,dtype=np.uint8)
    raise ValueError(pattern)

def phase(profile,rng,ns=SPS,initial_cfo=0,phi0=0):
    t=np.arange(N*ns)/(1200*ns);sign=int(rng.choice([-1,1]));p=phi0+2*np.pi*initial_cfo*t
    if profile.startswith('residual'):p=p+2*np.pi*({'residual002':.02,'residual010':.10}[profile])*1200*t
    elif profile.startswith('ramp'):p=p+sign*np.pi*float(profile[4:])*t*t
    elif profile.startswith('walk'):
        sigma=np.deg2rad(float(profile[4:]))/np.sqrt(ns)
        p=p+np.cumsum(rng.normal(0,sigma,size=len(t)))
    elif profile!='static':raise ValueError(profile)
    return p,sign

def make_case(pattern,profile,eb,seed,stage,trial):
    profiles=PROFILES if stage=='detector' else FULL_PROFILES
    ei=0 if eb=='clean' else [4,8,12].index(eb)+1
    rng=np.random.default_rng(np.random.SeedSequence([seed,0 if stage=='detector' else 1,PATTERNS.index(pattern),profiles.index(profile),ei,trial]))
    data=payload(pattern,rng);native=np.packbits(data).tobytes();sequence=int(rng.integers(0,2**32))
    wire=frame(native,sequence);truth=np.unpackbits(np.frombuffer(wire,np.uint8));states=np.cumsum(truth)%2
    f0=0. if stage=='detector' else float(rng.uniform(-8000,8000))
    phi0=float(rng.uniform(-np.pi,np.pi));gain=float(2**rng.uniform(-1,1))
    angle,direction=phase(profile,rng,initial_cfo=f0,phi0=phi0)
    oscillator=np.exp(1j*angle);h=oscillator.reshape(N,SPS).mean(axis=1)
    n0=0. if eb=='clean' else 10**(-eb/10)
    meta=dict(stage=stage,pattern=pattern,profile=profile,ebn0_db=eb,seed=seed,trial=trial,
              native_hex=native.hex(),rf_sequence=sequence,initial_cfo_hz=f0,phase0_rad=phi0,gain=gain,
              drift_direction=direction,payload_mean_symbol_energy=float(np.mean(abs(MU[states[PAYLOAD]])**2)))
    if stage=='detector':
        w=(rng.normal(size=N)+1j*rng.normal(size=N))*np.sqrt(n0/2)
        z=gain*(MU[states]*h+w)
        return meta,truth,z,h,gain
    start=int(rng.integers(24000,120001));x=(rng.normal(size=192000)+1j*rng.normal(size=192000))*np.sqrt(n0/2)
    x[start:start+N*SPS]+=np.repeat(MU[states],SPS)*oscillator/np.sqrt(SPS)
    x*=gain;meta['true_start_sample']=start;meta['input_iq_sha256']=hashlib.sha256(x.tobytes()).hexdigest()
    return meta,truth,x,h,gain

def decoded(hexdata):
    b=np.unpackbits(np.frombuffer(bytes.fromhex(hexdata),np.uint8)).astype(np.int8);b[0]=-1;return b

def metrics(bits,truth,aligned=True):
    if bits is None or not aligned:return dict(scored_bits=0,payload_errors=None,packet_pass=False)
    ix=PAYLOAD;errors=ix[np.asarray(bits)[ix]!=truth[ix]]
    sync=int(np.sum(np.asarray(bits)[256:288]!=truth[256:288]));crc=bool(crc_observation(bits))
    return dict(scored_bits=304,payload_errors=len(errors),zero_bits=int(np.sum(truth[ix]==0)),
       one_bits=int(np.sum(truth[ix]==1)),false_changes=int(np.sum(truth[errors]==0)),
       missed_changes=int(np.sum(truth[errors]==1)),preamble_errors=int(np.sum(np.asarray(bits)[PREAMBLE]!=truth[PREAMBLE])),
       payload_exact=len(errors)==0,sync_errors=sync,outer_crc_pass=crc,
       packet_pass=bool(sync==0 and crc and np.array_equal(np.asarray(bits)[256:680],truth[256:680])))

def detectors(z,h,gain):
    sign=np.full(N,-1,dtype=np.int8);sign[1:]=(np.real(z[1:]*z[:-1].conj())<0).astype(np.int8)
    pair=v4.pair.pair_glrt(z,MU);sequence=v4.sequence_glrt(z,MU,MODEL['sequence_window'])[0]
    expected=gain*h[:,None]*MU[None,:];states=np.argmin(abs(z[:,None]-expected)**2,axis=1)
    oracle=np.full(N,-1,dtype=np.int8);oracle[1:]=states[1:]^states[:-1]
    return dict(sign=sign,pair=pair,sequence=sequence,oracle_channel=oracle)
