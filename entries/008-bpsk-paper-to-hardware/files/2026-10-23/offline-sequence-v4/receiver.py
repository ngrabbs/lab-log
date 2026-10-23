"""Offline sequence decisions after unchanged v2 acquisition.
Overlapping local GLRT windows share a binary-state path via a Viterbi trellis.
No payload, preamble bits, sync bits or CRC constrain that path. This is a
composite profile-likelihood objective, not exact whole-frame AWGN ML.
"""
import importlib.util
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent.parent/'offline-geometry-v3'
spec=importlib.util.spec_from_file_location('pair_v3',BASE/'receiver.py')
pair=importlib.util.module_from_spec(spec);spec.loader.exec_module(pair)

def sequence_glrt(symbols,centers,window):
    z=np.asarray(symbols,dtype=np.complex128);mu=np.asarray(centers,dtype=np.complex128)
    if z.ndim!=1 or mu.shape!=(2,) or not np.isfinite(z).all() or not np.isfinite(mu).all():
        raise ValueError('Finite symbol vector and two finite centers required')
    if not isinstance(window,int) or not 2<=window<=9 or len(z)<window:
        raise ValueError('Window must be 2..9 and fit the symbol vector')
    patterns=(np.arange(1<<window)[:,None]>>np.arange(window-1,-1,-1))&1
    templates=mu[patterns];energy=np.sum(abs(templates)**2,axis=1)
    if np.any(energy<=0):raise ValueError('Nonzero template energies required')
    observations=np.lib.stride_tricks.sliding_window_view(z,window)
    scores=abs(observations@templates.conj().T)**2/energy
    # State = previous window-1 binary phase states. Both initial states free.
    memory=1<<(window-1);s=np.arange(memory)
    initial=np.stack([scores[0,s],scores[0,s+memory]],axis=1)
    initial_choice=np.argmax(initial,axis=1);cost=initial[s,initial_choice]
    previous=np.stack([s>>1,(s>>1)+(memory>>1)],axis=1)
    pattern=2*previous+(s&1)[:,None]
    back=np.empty((len(scores),memory),dtype=np.uint16)
    for k in range(1,len(scores)):
        options=cost[previous]+scores[k,pattern]
        choice=np.argmax(options,axis=1)
        cost=options[s,choice];back[k]=previous[s,choice]
    state=int(np.argmax(cost));best=float(cost[state])
    states=np.empty(len(z),dtype=np.int8)
    for k in range(len(scores)-1,0,-1):
        states[k+window-1]=state&1;state=int(back[k,state])
    states[:window]=patterns[state+int(initial_choice[state])*memory]
    bits=np.full(len(z),-1,dtype=np.int8);bits[1:]=states[1:]^states[:-1]
    return bits,states,best

def symbols_at(iq,result):
    k=result['start_sample'];f=result['cfo_hz']
    a=np.asarray(iq,dtype=np.complex128)[k:k+808*40]*np.exp(-2j*np.pi*f*np.arange(808*40)/48000)
    return a.reshape(808,40).sum(axis=1)/np.sqrt(40)

def replace_bits(result,z,model,window):
    if not result['detected']:return result
    original=result['bits']
    result['sign_decisions_hex']=result['baseline_decisions_hex']
    result['baseline_decisions_hex']=np.packbits(np.maximum(original,0).astype(np.uint8)).tobytes().hex()
    result['baseline_sync_errors']=result['sync_errors']
    mu=np.array([complex(*v) for v in model['centers']])
    bits,states,cost=sequence_glrt(z,mu,window)
    sync=np.unpackbits(np.frombuffer(bytes.fromhex('1acffc1d'),np.uint8))
    result.update(bits=bits,sync_errors=int(np.sum(bits[256:288]!=sync)),detector='window_glrt_trellis',sequence_window=window)
    return result

def acquire(iq,model):
    result=pair.acquire(iq,model)
    if not result['detected']:return result
    return replace_bits(result,symbols_at(iq,result),model,model['sequence_window'])
