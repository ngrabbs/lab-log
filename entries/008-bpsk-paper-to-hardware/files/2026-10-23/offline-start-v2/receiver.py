"""Offline unknown-start/CFO receiver. Inputs are IQ and a frozen training model only.
No capture metadata, timing, CFO, expected body or CRC is used in acquisition.
V2 ranks frame starts by separately normalized preamble and sync correlations.
"""
import numpy as np
RATE=48000
SPS=40

def known_template(model):
    bits=np.unpackbits(np.frombuffer(bytes([0x55])*32+bytes.fromhex('1acffc1d'),np.uint8))
    states=np.cumsum(bits)%2
    mu=np.array([complex(*v) for v in model['centers']])
    t=np.repeat(mu[states],SPS)
    mask=np.repeat((np.arange(288)<64)|(np.arange(288)>=256),SPS)
    return t*mask,mask

def correlation_search(x,model):
    """Prepare two independent complex-amplitude fits, avoiding phase coupling
    over the 192-symbol gap between training preamble and unique sync.
    The geometric mean requires support from both fields. No payload/CRC fit.
    """
    n=len(x);template,mask=known_template(model);m=len(template)
    nf=1<<(n+m-2).bit_length()
    regions=[np.arange(m)<64*SPS,np.arange(m)>=256*SPS]
    spectra=[];energies=[];templates=[]
    power_fft=np.fft.rfft(abs(x)**2,nf)
    for region in regions:
        t=template*region
        e=np.fft.irfft(power_fft*np.fft.rfft(region[::-1].astype(float),nf),nf)[m-1:n]
        spectra.append(np.fft.fft(t[::-1].conj(),nf))
        energies.append(e);templates.append(t)
    def search(freq):
        a=x*np.exp(-2j*np.pi*freq*np.arange(n)/RATE)
        ft=np.fft.fft(a,nf);scores=[]
        for spec,e,t in zip(spectra,energies,templates):
            c=np.fft.ifft(ft*spec)[m-1:n]
            score=abs(c)**2/np.maximum(e*np.sum(abs(t)**2),1e-30)
            score[e<max(float(e.max())*1e-8,1e-30)]=0
            scores.append(np.clip(score,0,1))
        joint=np.sqrt(scores[0]*scores[1])
        joint[max(0,n-808*SPS+1):]=0
        k=int(np.argmax(joint))
        return float(joint[k]),k,[float(v[k]) for v in scores]
    def refine(k,f):
        # Independently fit the phase of each field at each CFO hypothesis.
        # This objective has no artificial long-gap coherent fringes.
        t=np.arange(m)/RATE
        segments=[x[k:k+m]*v.conj() for v in templates]
        for spacing in (1.,.1):
            fs=f+np.arange(-5,6)*spacing
            oscillator=np.exp(-2j*np.pi*fs[:,None]*t)
            values=np.sqrt(abs(oscillator@segments[0])**2*abs(oscillator@segments[1])**2)
            f=float(fs[np.argmax(values)])
        return f
    return search,refine

def acquire(iq,model):
    x=np.asarray(iq,dtype=np.complex128)
    if x.ndim!=1 or len(x)<808*SPS or not np.isfinite(x).all() or not np.any(x):
        return {'detected':False,'reason':'invalid_or_short'}
    # Search every 1280-sample window. The 64-symbol preamble is periodic;
    # all four symbol phases and the strongest three separated spectral peaks
    # are searched, within the fixed +/-12 kHz design range.
    mu=np.array([complex(*v) for v in model['centers']])
    period=np.repeat(mu[[0,1,1,0]],SPS)
    length=64*SPS;nf=65536
    best=(-1,None)
    for start in range(0,len(x)-length+1,1280):
        a=x[start:start+length]
        for phase in range(4):
            t=np.tile(np.roll(period,phase*SPS),16)
            p=abs(np.fft.fft(a*t.conj(),nf))**2
            p[nf//4:3*nf//4]=0
            score=float(p.max()/(np.sum(abs(a)**2)*np.sum(abs(t)**2)+1e-30))
            if score>best[0]:best=(score,(p,start,phase))
    p,start,phase=best[1];candidates=[]
    for _ in range(3):
        k=int(np.argmax(p));l=np.log(np.maximum(p[[(k-1)%nf,k,(k+1)%nf]],1e-100))
        den=l[0]-2*l[1]+l[2]
        delta=float(.5*(l[0]-l[2])/den) if abs(den)>1e-15 else 0.
        signed=k if k<nf//2 else k-nf
        candidates.append((signed+delta)*RATE/nf)
        for offset in range(-14,15):p[(k+offset)%nf]=0
    search,refine=correlation_search(x,model)
    trials=[]
    for f in candidates:
        for offset in (-4,0,4):
            score,k,blocks=search(f+offset)
            trials.append((score,k,f+offset,blocks))
    score,k,f,blocks=max(trials,key=lambda v:v[0])
    f=refine(k,f)
    score,k,blocks=search(f)
    if score<model['threshold']:
        return dict(detected=False,reason='below_threshold',metric=score,coarse_metric=best[0])
    a=x[k:k+808*SPS]*np.exp(-2j*np.pi*f*np.arange(808*SPS)/RATE)
    z=a.reshape(808,SPS).sum(axis=1)/np.sqrt(SPS)
    bits=np.full(808,-1,dtype=np.int8)
    bits[1:]=(np.real(z[1:]*z[:-1].conj())<0).astype(np.int8)
    sync=np.unpackbits(np.frombuffer(bytes.fromhex('1acffc1d'),np.uint8))
    return dict(detected=True,start_sample=k,cfo_hz=f,metric=score,
                coarse_metric=best[0],block_metrics=blocks,sync_errors=int(np.sum(bits[256:288]!=sync)),bits=bits)
