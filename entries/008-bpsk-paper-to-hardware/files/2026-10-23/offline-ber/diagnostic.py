"""Offline BPSK diagnostics. No radio, serial, sockets, CRC gating or live decoder changes.

All symbol indices refer to logical transmitted symbols. Differential bit k uses
symbols k-1 and k; bit 0 has no observed predecessor and is explicitly unscorable.
CRC is an output observation, never a condition for returning/scoring decisions.
"""
import math
import struct
import zlib
import numpy as np
SPS=40
RATE=48000
TRAIN=np.arange(4,64)
SCORE=np.arange(68,252)  # 184 independently known 0x55 preamble bits, outside training
SYNC=bytes.fromhex('1acffc1d')

def frame(native,sequence):
    body=struct.pack('>BIH',3,sequence,len(native))+native
    return bytes([0x55])*32+SYNC+body+struct.pack('>I',zlib.crc32(body))+bytes(16)

def frame_reference(native_hex,sequence):
    bits=np.unpackbits(np.frombuffer(frame(bytes.fromhex(native_hex),sequence),np.uint8))
    return bits,(np.cumsum(bits)%2).astype(np.uint8)

def integrate(iq,start,nsymbols=808,sps=SPS):
    a=np.asarray(iq)[start:start+nsymbols*sps]
    if len(a)!=nsymbols*sps:raise ValueError('Scheduled symbol window incomplete')
    return a.reshape(nsymbols,sps).sum(axis=1)/math.sqrt(sps)

def decisions(symbols,centers):
    z=np.asarray(symbols)
    coherent=(abs(z-centers[1])**2<abs(z-centers[0])**2).astype(np.int8)
    differential=np.full(z.shape,-1,dtype=np.int8)
    differential[...,1:]=(np.real(z[...,1:]*np.conj(z[...,:-1]))<0).astype(np.int8)
    return coherent,differential

def score_bits(bits,expected,indices=SCORE):
    bits=np.asarray(bits);idx=np.asarray(indices)
    if len(bits)<=int(idx.max()) or np.any(bits[idx]<0) or not np.isfinite(bits[idx]).all():
        return dict(scorable=False,scored_bits=0,bit_errors=None,error_positions=[])
    positions=idx[bits[idx]!=np.asarray(expected)[idx]]
    return dict(scorable=True,scored_bits=len(idx),bit_errors=len(positions),error_positions=positions.tolist())

def crc_observation(bits,expected_native_bytes=38):
    """Fixed scheduled body length, never read a noisy header to choose BER window."""
    bits=np.asarray(bits)
    begin=288;end=begin+(7+expected_native_bytes+4)*8
    if len(bits)<end or np.any(bits[begin:end]<0):return False
    wire=np.packbits(bits[begin:end]).tobytes()
    return (wire[0]==3 and int.from_bytes(wire[5:7],'big')==expected_native_bytes
            and zlib.crc32(wire[:-4])==int.from_bytes(wire[-4:],'big'))

def freeze(iq,source):
    """Clean-reference scheduling/calibration. No noisy payload/error minimization.

    One CFO is taken from the previously recorded clean common-slope estimate.
    Choose one rectangular-integration timing using only known preamble TRAIN.
    Geometry estimates may be trained here because this is explicitly an oracle
    replay bound, not an unknown-channel receiver or blind acquisition result.
    """
    iq=np.asarray(iq,dtype=np.complex128)
    if iq.ndim!=1 or not np.isfinite(iq).all():raise ValueError('Invalid clean IQ')
    bits,states=frame_reference(source['native_hex'],source['rf_sequence'])
    base=source['preamble_start_symbol']*SPS+source['timing_sample']
    corrected=iq*np.exp(-2j*np.pi*source['refined_cfo_hz']*np.arange(len(iq))/RATE)
    candidates=[]
    for offset in range(-20,20):
        z=integrate(corrected,base+offset,len(bits))
        mu=np.array([z[TRAIN][states[TRAIN]==s].mean() for s in (0,1)])
        metric=np.mean(abs(z[TRAIN]-mu[states[TRAIN]])**2)/np.mean(abs(z[TRAIN])**2)
        candidates.append((float(metric),offset,z,mu))
    metric,offset,z,mu=min(candidates,key=lambda x:x[0])
    start=base+offset
    idle=corrected[:RATE]
    idle_power=float(np.mean(abs(idle)**2))
    active=corrected[start:start+256*SPS]
    observed_energy=SPS*(float(np.mean(abs(active)**2))-idle_power)
    if observed_energy<=0:raise ValueError('Nonpositive reference symbol energy')
    scale=math.sqrt(observed_energy)
    normalized=iq/scale;z/=scale;mu/=scale
    idle_z=integrate(corrected/scale,0,RATE//SPS)
    existing_noise=float(np.mean(abs(idle_z-idle_z.mean())**2))
    coherent,diff=decisions(z,mu)
    coarse_energy=float(np.mean(abs(active/scale)**2)*SPS)
    return dict(native_bytes=len(bytes.fromhex(source['native_hex'])),start_sample=start,nominal_start_sample=base,selected_offset_samples=offset,
        cfo_hz=source['refined_cfo_hz'],training_variance_metric=metric,
        energy_before_normalization=observed_energy,normalized_observed_symbol_energy=coarse_energy,
        existing_matched_filter_noise_variance=existing_noise,
        centers=[[float(v.real),float(v.imag)] for v in mu],
        integrated_center_separation_deg=float(abs(np.angle(mu[1]*mu[0].conjugate()))*180/np.pi),
        known_preamble_baseline=score_bits(diff,bits),coherent_phase_baseline=score_bits(coherent,states),
        original_frame_crc_pass=crc_observation(diff,len(bytes.fromhex(source['native_hex']))),symbols=z,normalized_iq=normalized,
        expected_bits=bits,expected_states=states)

def square_cfo(iq):
    a=np.asarray(iq,dtype=np.complex64)
    nfft=1<<(len(a)*4-1).bit_length()
    k=int(np.argmax(abs(np.fft.fft(a*a,nfft))))
    if k>=nfft//2:k-=nfft
    return k*RATE/nfft/2

def choose_training_timing(corrected,nominal_start,expected_bits,nsymbols):
    offsets=np.arange(-20,20)
    bounds=nominal_start+offsets[:,None]+np.arange(nsymbols+1)[None,:]*SPS
    if bounds.min()<0 or bounds.max()>len(corrected):raise ValueError('Incomplete scheduled search window')
    integ=np.r_[0,np.cumsum(corrected)]
    z=np.diff(integ[bounds],axis=1)/math.sqrt(SPS)
    product=z[:,TRAIN]*np.conj(z[:,TRAIN-1])
    signed=(1-2*np.asarray(expected_bits[TRAIN],dtype=float))[None,:]
    metric=np.sum(signed*product.real,axis=1)/(np.sum(abs(product),axis=1)+1e-30)
    selected=int(np.argmax(metric))
    return z[selected],int(offsets[selected]),float(metric[selected])

def template_cfo(iq,ref):
    """Paper-style ML periodogram adapted to a learned 64-symbol HW template.
    Scheduled timing/clean state means are supplied; not a blind/live receiver.
    Only preamble symbols 0..63 contribute; scored bits start at 68.
    """
    centers=np.array([complex(*v) for v in ref['centers']])
    template=np.repeat(centers[ref['expected_states'][:64]],SPS)/math.sqrt(SPS)
    start=ref['start_sample'];segment=np.asarray(iq)[start:start+len(template)]
    nfft=1<<(len(template)*16-1).bit_length()
    spectrum=abs(np.fft.fft(segment*np.conj(template),nfft))
    k=int(spectrum.argmax());left,mid,right=spectrum[(k-1)%nfft],spectrum[k],spectrum[(k+1)%nfft]
    denom=left-2*mid+right;delta=.5*(left-right)/denom if denom!=0 else 0.
    f=(k+delta)/nfft
    if f>=.5:f-=1
    return f*RATE

def scheduled_diagnostic(iq,ref,carrier_method="square"):
    """Known scheduled 4s window; noisy squared CFO + training-only timing search.

    This replaces the live receiver's CRC-based timing acceptance with a fixed
    known-preamble metric so every failed decision survives. It is NOT a faithful
    measurement of blind burst discovery or of the operational CRC-search policy.
    """
    iq=np.asarray(iq)
    if iq.ndim!=1 or not np.isfinite(iq).all():return dict(scorable=False,reason='Invalid IQ',scored_bits=0)
    if len(iq)<ref['nominal_start_sample']+len(ref['expected_bits'])*SPS+20:return dict(scorable=False,reason='Incomplete scheduled IQ window',scored_bits=0)
    if carrier_method not in ('square','template'):raise ValueError('Unknown carrier method')
    cfo=square_cfo(iq) if carrier_method=="square" else template_cfo(iq,ref)
    corrected=iq*np.exp(-2j*np.pi*cfo*np.arange(len(iq))/RATE)
    z,offset,metric=choose_training_timing(corrected,ref['nominal_start_sample'],ref['expected_bits'],len(ref['expected_bits']))
    centers=np.array([complex(*p) for p in ref['centers']])
    _,bits=decisions(z,centers)
    scored=score_bits(bits,ref['expected_bits'])
    return dict(**scored,bits=bits,carrier_estimate_hz=cfo,timing_offset_samples=offset,
        training_metric=metric,sync_exact=bool(np.all(bits[256:288]==ref['expected_bits'][256:288])),
        outer_crc32_pass=crc_observation(bits,ref["native_bytes"]),
        scheduled_frame_pass=bool(np.all(bits[256:288]==ref['expected_bits'][256:288]) and crc_observation(bits,ref["native_bytes"])),
        replay_reference_body_errors=int(np.count_nonzero(bits[288:len(ref['expected_bits'])-128]!=ref['expected_bits'][288:len(ref['expected_bits'])-128])))

def cluster_interval(errors,nbits):
    """Trial-block normal interval; zero-error bound uses independent trials,
    not a fictitious number of independent differential bit errors.
    """
    e=np.asarray(errors,dtype=float);n=len(e)
    if n==0:return None,None,None,'No scorable trials'
    ber=float(e.sum()/(n*nbits))
    if not np.any(e):
        return 0.,0.,float(1-.05**(1/n)),'one-sided 95% independent-trial bound on BER <= P(any trial error)'
    se=float(np.std(e/nbits,ddof=1)/math.sqrt(n))
    return ber,max(0.,ber-1.96*se),min(1.,ber+1.96*se),'95% trial-block normal interval; sparse tails flagged'


def main():
    """Decode a scheduled replay while retaining failed decisions."""
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=Path(__file__).resolve().parent/'manifest.json')
    p.add_argument('--capture',required=True)
    p.add_argument('--iq',type=Path,help='Optional noisy IQ; default is clean reference. NPY or NPZ iq array.')
    p.add_argument('--normalized',action='store_true',help='Supplied noisy IQ already uses normalized replay energy')
    p.add_argument('--mode',choices=['frozen','square','template'],default='square')
    p.add_argument('--output',type=Path)
    a=p.parse_args();manifest=json.loads(a.manifest.read_text());source=next(s for s in manifest['sources'] if s['name']==a.capture)
    def load(path):
        x=np.load(path,allow_pickle=False)
        return x['iq'] if isinstance(x,np.lib.npyio.NpzFile) else x
    clean=load(a.manifest.parent/source['filename']);ref=freeze(clean,source)
    iq=ref['normalized_iq'] if a.iq is None else load(a.iq)/(1 if a.normalized else math.sqrt(ref['energy_before_normalization']))
    if iq.ndim!=1 or not np.isfinite(iq).all() or len(iq)<ref['start_sample']+len(ref['expected_bits'])*SPS:
        r=dict(scorable=False,reason='Invalid or incomplete scheduled IQ',scored_bits=0)
    elif a.mode=='frozen':
        z=integrate(iq*np.exp(-2j*np.pi*ref['cfo_hz']*np.arange(len(iq))/RATE),ref['start_sample'],len(ref['expected_bits']))
        _,bits=decisions(z,np.array([complex(*c) for c in ref['centers']]))
        r=dict(**score_bits(bits,ref['expected_bits']),bits=bits,outer_crc32_pass=crc_observation(bits,ref['native_bytes']))
    else:r=scheduled_diagnostic(iq,ref,a.mode)
    if 'bits' in r:
        bits=r.pop('bits');r['decisions_hex']=np.packbits(np.maximum(bits,0).astype(np.uint8)).tobytes().hex();r['unobserved_bit_indices']=[0]
    result=dict(capture=a.capture,mode=a.mode,ground_truth='Known held-out preamble only; payload is a clean-decode replay reference.',**r)
    text=json.dumps(result,indent=2)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')

if __name__=='__main__':main()
