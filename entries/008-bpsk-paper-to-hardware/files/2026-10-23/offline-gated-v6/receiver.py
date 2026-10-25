"""Offline pilot-drift and decision-confidence gated carrier tracking.
Acquisition, geometry, initializer and final free sequence path are inherited.
The late pilot makes the frame gate noncausal; no truth/CRC chooses a branch.
"""
from pathlib import Path
import importlib.util
import numpy as np
BASE=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('tracking_v5',BASE/'offline-tracking-v5/receiver.py')
v5=importlib.util.module_from_spec(spec);spec.loader.exec_module(v5)
v4=v5.v4
centers=v5.centers;preamble_states=v5.preamble_states;locate=v5.locate

def pilot_fit(z,mu,states):
    known=mu[states];n=np.arange(len(z));t=n/1200
    f=v5.peak_frequency(z*known.conj(),1200,[-300,300],16384)
    a=np.vdot(known*np.exp(2j*np.pi*f*t),z)/np.vdot(known,known).real
    fitted=a*known*np.exp(2j*np.pi*f*t)
    residual=z-fitted
    noise=max(float(np.mean(abs(residual)**2)),np.finfo(float).eps*max(float(np.mean(abs(z)**2)),1e-300))
    # Phase-slope SE is an AWGN-style heuristic; correlated walk noise is not
    # assumed calibrated Gaussian confidence. Neither pilot supplies true CFO.
    phase=np.angle(z*fitted.conj())
    centered=t-t.mean();slope=float(np.dot(centered,phase)/np.dot(centered,centered))
    errors=phase-phase.mean()-slope*centered
    sigma2=float(np.sum(errors**2)/max(1,len(z)-2))
    se=np.sqrt(max(sigma2,1e-16)/np.dot(centered,centered))/(2*np.pi)
    return dict(frequency_hz=f,frequency_se_hz=float(se),noise_variance=noise,
                gain=a,pilot_phase_rms_rad=float(np.sqrt(sigma2)))

def prepare(z,model):
    z=np.asarray(z,dtype=np.complex128)
    if z.ndim!=1 or len(z)!=808 or not np.isfinite(z).all():raise ValueError('808 finite symbols required')
    mu=centers(model);states=preamble_states()
    early=pilot_fit(z[:64],mu,states[:64]);late=pilot_fit(z[224:288],mu,states[224:288])
    delta=late['frequency_hz']-early['frequency_hz'];se=np.hypot(early['frequency_se_hz'],late['frequency_se_hz'])
    return z,mu,early,dict(pilot_frequency_difference_hz=float(delta),drift_rate_hz_s=float(delta/(224/1200)),
            drift_score=float(abs(delta)/max(se,1e-12)),early_frequency_hz=early['frequency_hz'],
            late_frequency_hz=late['frequency_hz'],early_frequency_se_hz=early['frequency_se_hz'],
            late_frequency_se_hz=late['frequency_se_hz'])

def gated_prepared(prepared,model):
    z,mu,early,info=prepared;info=info.copy()
    enable=bool(info['drift_score']>=model['gate_drift_score'] and abs(info['drift_rate_hz_s'])>=model['gate_min_drift_hz_s'])
    info['tracking_enabled']=enable
    if not enable:
        corrected,base=v5.track_symbols(z,model,0.)
        info.update(base);info.update(accepted_updates=0,possible_updates=744)
        return v4.sequence_glrt(corrected,mu,3)[0],info
    a=early['gain'];amplitude=max(abs(a),1e-15);phi0=np.angle(a);omega=2*np.pi*early['frequency_hz']/1200
    alpha=model['tracking_alpha'];beta=alpha**2/4;phi=phi0+64*omega
    corrected=np.empty_like(z);corrected[:64]=z[:64]*np.exp(-1j*(phi0+omega*np.arange(64)))
    accepted=0;errors=[]
    for k in range(64,len(z)):
        corrected[k]=z[k]*np.exp(-1j*phi)
        distance=abs(corrected[k]-amplitude*mu)**2;state=int(np.argmin(distance))
        confidence=float(abs(distance[1]-distance[0])/early['noise_variance'])
        innovation=float(np.clip(np.angle(corrected[k]*mu[state].conjugate()),-np.pi/3,np.pi/3))
        # Rejected innovations do not change phase/frequency estimates; the NCO
        # still propagates its existing frequency through the rejected symbol.
        if confidence>=model['gate_decision_gap']:
            omega+=beta*innovation;phi+=alpha*innovation;accepted+=1;errors.append(innovation)
        phi+=omega
    bits=v4.sequence_glrt(corrected,mu,3)[0]
    info.update(residual_cfo_hz=early['frequency_hz'],ending_residual_hz=float(omega*1200/(2*np.pi)),
        accepted_updates=accepted,possible_updates=744,innovation_rms_rad=float(np.sqrt(np.mean(np.array(errors)**2))) if errors else 0.)
    return bits,info

def detect_symbols(z,model,alpha=None):
    # alpha=0 exposes the exact inherited preamble-only ablation.
    if alpha is not None:return v5.detect_symbols(z,model,alpha)
    return gated_prepared(prepare(z,model),model)

def acquire(iq,model):
    result=locate(iq,model)
    if not result['detected']:return result
    bits,info=detect_symbols(v4.symbols_at(iq,result),model)
    sync=np.unpackbits(np.frombuffer(bytes.fromhex('1acffc1d'),np.uint8))
    result.update(info);result.update(bits=bits,sync_errors=int(np.sum(bits[256:288]!=sync)),
        detector='pilot_drift_and_decision_confidence_gated_sequence',sequence_window=3)
    return result
