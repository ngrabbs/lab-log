"""Offline drift-tolerant acquisition and preamble-initialized tracking.
No timing, frequency, payload truth or CRC enters the receiver. Final path is
an unconstrained overlapping-window composite GLRT, inherited unchanged.
"""
from pathlib import Path
import importlib.util
import numpy as np
BASE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('sequence_v4',BASE/'offline-sequence-v4/receiver.py')
v4=importlib.util.module_from_spec(spec);spec.loader.exec_module(v4)

def centers(model):return np.array([complex(*v) for v in model['centers']])
def preamble_states():
    bits=np.unpackbits(np.frombuffer(b'\x55'*32+bytes.fromhex('1acffc1d'),np.uint8))
    return np.cumsum(bits)%2

def peak_frequency(y,rate,bounds,nfft):
    power=abs(np.fft.fft(y,nfft))**2;freq=np.fft.fftfreq(nfft,1/rate)
    valid=(freq>=bounds[0])&(freq<=bounds[1]);power[~valid]=-np.inf
    k=int(np.argmax(power));a,b,c=power[(k-1)%nfft],power[k],power[(k+1)%nfft]
    delta=.5*(a-c)/(a-2*b+c) if np.isfinite(a+c) and a-2*b+c!=0 else 0.
    return float(freq[k]+np.clip(delta,-.5,.5)*rate/nfft)

def locate(iq,model):
    x=np.asarray(iq,dtype=np.complex128)
    if x.ndim!=1 or len(x)<808*40 or not np.isfinite(x).all() or np.max(abs(x))==0:
        return dict(detected=False,metric=0.)
    mu=centers(model);t=np.repeat(mu[preamble_states()[224:288]],40)
    d=x[40:]*x[:-40].conj();td=t[40:]*t[:-40].conj()
    size=1<<(len(d)+len(td)-2).bit_length()
    corr=np.fft.ifft(np.fft.fft(d,size)*np.fft.fft(td[::-1].conj(),size))[len(td)-1:len(d)]
    energy=np.r_[0.,np.cumsum(abs(d)**2)]
    energy=energy[len(td):]-energy[:-len(td)]
    # FFT convolution leaves roundoff in mathematically empty windows. Never
    # normalize that residue by zero; eps*total is a numerical resolvability
    # bound, not a fitted signal/noise threshold.
    valid=energy>np.finfo(float).eps*float(np.sum(abs(d)**2))
    score=np.zeros_like(energy)
    score[valid]=abs(corr[valid])**2/(energy[valid]*np.vdot(td,td).real)
    score=np.clip(score,0.,1.)
    lo=224*40;hi=len(x)-808*40+lo
    score[:lo]=0;score[hi+1:]=0
    candidates=[];local=score.copy();n=np.arange(len(t))
    for _ in range(model.get('acquisition_candidates',8)):
        b=int(np.argmax(local));dscore=float(local[b]);local[max(0,b-80):b+81]=0
        f=peak_frequency(x[b:b+len(t)]*t.conj(),48000,model['cfo_search_hz'],65536)
        for iteration in range(2):
            starts=np.arange(max(lo,b-40),min(hi,b+40)+1)
            chunks=np.lib.stride_tricks.sliding_window_view(x,len(t))[starts]
            template=t*np.exp(2j*np.pi*f*n/48000)
            e=np.sum(abs(chunks)**2,axis=1)*np.vdot(t,t).real
            values=abs(chunks@template.conj())**2/np.maximum(e,1e-300)
            best=int(np.argmax(values));b=int(starts[best]);metric=float(values[best])
            f=peak_frequency(x[b:b+len(t)]*t.conj(),48000,model['cfo_search_hz'],65536)
        candidates.append((metric,b,f,dscore))
    metric,b,f,ds=max(candidates)
    return dict(detected=bool(metric>=model['threshold']),start_sample=b-lo,cfo_hz=f,
                metric=metric,differential_metric=ds)

def track_symbols(z,model,alpha=None):
    z=np.asarray(z,dtype=np.complex128);mu=centers(model);known=mu[preamble_states()[:64]]
    if z.ndim!=1 or len(z)!=808 or not np.isfinite(z).all():raise ValueError('808 finite symbols required')
    if np.max(abs(z))==0:return z.copy(),dict(residual_cfo_hz=0.,ending_residual_hz=0.)
    f=peak_frequency(z[:64]*known.conj(),1200,[-300,300],16384)
    omega=2*np.pi*f/1200;n=np.arange(64)
    a=np.vdot(known*np.exp(1j*omega*n),z[:64])/np.vdot(known,known).real
    amplitude=max(abs(a),1e-15);phi0=np.angle(a)
    alpha=model['tracking_alpha'] if alpha is None else alpha;beta=alpha**2/4
    out=np.empty_like(z);out[:64]=z[:64]*np.exp(-1j*(phi0+omega*n))
    phi=phi0+64*omega;innov=[]
    for k in range(64,len(z)):
        out[k]=z[k]*np.exp(-1j*phi)
        state=int(np.argmin(abs(out[k]/amplitude-mu)**2))
        error=float(np.clip(np.angle(out[k]*mu[state].conjugate()),-np.pi/3,np.pi/3))
        innov.append(error);omega+=beta*error;phi+=omega+alpha*error
    return out,dict(residual_cfo_hz=f,ending_residual_hz=float(omega*1200/(2*np.pi)),
                    innovation_rms_rad=float(np.sqrt(np.mean(np.array(innov)**2))))

def detect_symbols(z,model,alpha=None):
    tracked,info=track_symbols(z,model,alpha)
    bits=v4.sequence_glrt(tracked,centers(model),3)[0]
    return bits,info

def acquire(iq,model):
    result=locate(iq,model)
    if not result['detected']:return result
    bits,info=detect_symbols(v4.symbols_at(iq,result),model)
    sync=np.unpackbits(np.frombuffer(bytes.fromhex('1acffc1d'),np.uint8))
    result.update(info);result.update(bits=bits,sync_errors=int(np.sum(bits[256:288]!=sync)),
        detector='differential_boundary_acquisition_pll_sequence',sequence_window=3)
    return result
