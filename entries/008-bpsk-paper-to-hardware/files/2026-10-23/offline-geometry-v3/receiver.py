"""Offline geometry-aware pair detector after unchanged v2 acquisition.
Only libre01 provides the state geometry. Each adjacent pair fits a nuisance
complex gain; no test geometry, payload, expected timing/CFO or CRC selects bits.
"""
import importlib.util
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent.parent/'offline-start-v2'
spec=importlib.util.spec_from_file_location('acquisition_v2',BASE/'receiver.py')
acquisition=importlib.util.module_from_spec(spec);spec.loader.exec_module(acquisition)

def pair_glrt(symbols,centers):
    """Minimize complex least-squares residual over 00,01,10,11 and one
    unknown complex scale per observed pair. Return XOR of selected states.
    This is a pairwise GLRT, not a coherent or sequence-optimal decoder.
    """
    z=np.asarray(symbols,dtype=np.complex128)
    mu=np.asarray(centers,dtype=np.complex128)
    if z.ndim!=1 or mu.shape!=(2,) or not np.isfinite(z).all() or not np.isfinite(mu).all():
        raise ValueError('Finite symbol vector and two finite centers required')
    templates=mu[np.array([[0,0],[0,1],[1,0],[1,1]])]
    energy=np.sum(abs(templates)**2,axis=1)
    if np.any(energy<=0):raise ValueError('Nonzero template energy required')
    bits=np.full(len(z),-1,dtype=np.int8)
    if len(z)<2:return bits
    pairs=np.stack([z[:-1],z[1:]],axis=1)
    scores=abs(pairs@templates.conj().T)**2/energy
    bits[1:]=np.array([0,1,1,0],dtype=np.int8)[np.argmax(scores,axis=1)]
    return bits

def acquire(iq,model):
    result=acquisition.acquire(iq,model)
    if not result['detected']:return result
    original=result['bits']
    result['baseline_decisions_hex']=np.packbits(np.maximum(original,0).astype(np.uint8)).tobytes().hex()
    result['baseline_sync_errors']=result['sync_errors']
    k=result['start_sample'];f=result['cfo_hz']
    a=np.asarray(iq,dtype=np.complex128)[k:k+808*40]*np.exp(-2j*np.pi*f*np.arange(808*40)/48000)
    z=a.reshape(808,40).sum(axis=1)/np.sqrt(40)
    mu=np.array([complex(*v) for v in model['centers']])
    bits=pair_glrt(z,mu)
    sync=np.unpackbits(np.frombuffer(bytes.fromhex('1acffc1d'),np.uint8))
    result.update(bits=bits,sync_errors=int(np.sum(bits[256:288]!=sync)),detector='pair_glrt')
    return result
