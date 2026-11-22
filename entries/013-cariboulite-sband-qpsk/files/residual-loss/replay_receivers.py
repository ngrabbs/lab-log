"""Receiver ablations and data-aided diagnostics for the archived QPSK IQ."""
import argparse
from pathlib import Path

import numpy as np
from scipy import signal

import iq_residual as iq
import qpsk_bench_shuffled as q


def sliced(value):
    return ((1-2*(value.real<0)) + 1j*(1-2*(value.imag<0))) / np.sqrt(2)


def block_fit(samples, symbols, width=192, step=64):
    # Fit the desired QPSK, conjugate leakage and constant independently.
    # For the blind decoder, symbols are decisions or the published preamble.
    centers, result = [], []
    last = len(samples)-1
    for mid in range(0,len(samples)+step-1,step):
        a, b = max(0,mid-width//2), min(last+1,mid+width//2)
        ref = symbols[a:b]
        design = np.column_stack((ref, ref.conj(), np.ones(len(ref))))
        fit = np.linalg.lstsq(design, samples[a:b], rcond=None)[0]
        centers.append((a+b-1)/2)
        result.append(fit)
    grid = np.arange(len(samples))
    model = np.array([np.interp(grid,centers,c) for c in np.array(result).T])
    return model


def symbol_replay(samples,rate):
    old, cal, pilot_evm = iq.baseline(samples,rate)
    hz,a,b,d = cal
    n = np.arange(len(samples))
    old_rotation = np.exp(-2j*np.pi*hz*n/rate)
    # Average over unknown payload symbols and compensate at the edges. The
    # known sync pilot is explicitly removed so its nonzero mean cannot bias it.
    cleaned = samples.copy()
    cleaned[:q.PILOT_LEN] -= (a*q.PILOT+b*q.PILOT.conj()) / old_rotation[:q.PILOT_LEN]
    win = np.hanning(385)
    dc = signal.convolve(cleaned,win,mode='same') / signal.convolve(np.ones(len(cleaned)),win,mode='same')
    dc_only = q.track_payload_phase((samples-dc)/a)
    reference = sliced(dc_only)
    reference[:q.PILOT_LEN] = q.PILOT
    gain,image,tracked_dc = block_fit(samples,reference)
    centered = samples-tracked_dc
    fitted = (gain.conj()*centered-image*centered.conj()) / (abs(gain)**2-abs(image)**2)
    # Isolate the effect of changing the leakage estimate in the old chain.
    after_dc = q.equalize(samples+(d/old_rotation-tracked_dc),n,rate,cal)
    dd_dc_only = q.track_payload_phase(after_dc)
    fixed_cfo = q.track_payload_phase(q.equalize(samples,n,rate,(0,a,b,d)))
    return {'baseline':old,'zero_pilot_cfo':fixed_cfo,
            'local_mean_leakage':dc_only,'decision_directed_leakage':dd_dc_only,
            'joint_decision_directed':fitted}, cal, pilot_evm


def replay(cache, seed, order, out, detail=True):
    archive = np.load(cache)
    rate = int(archive['rate'])
    rows=[]
    model_rows=[]
    refs = iq.expected_bytes(seed,order)
    for slot,(samples, expected) in enumerate(zip(archive['symbols'],refs)):
        values,cal,evm = symbol_replay(samples,rate)
        for mode,value in values.items():
            packet = iq.hard(value[q.PILOT_LEN:])
            e = iq.per_symbol_errors(packet,expected)
            counts=e.reshape(10,208).sum(axis=1)
            rows.append({'position':slot,'mode':mode,'valid':int(iq.crc_ok(packet) and packet==expected),
                         'crc_ok':int(iq.crc_ok(packet)),'bit_errors':int(e.sum()),
                         **{f'errors_decile_{i}':v for i,v in enumerate(counts,1)}})
        if not detail:
            continue
        ideal = np.r_[q.PILOT,q.qpsk(np.unpackbits(np.frombuffer(expected,dtype=np.uint8)))]
        # The transmitted bytes are used only here, after receiver decisions,
        # to estimate how the underlying model changed during the frame.
        true_gain,true_image,true_dc = block_fit(samples,ideal)
        hz,gain,image,dc = cal
        model_hz = lambda x:float(np.polyfit(np.arange(len(x))/rate,np.unwrap(np.angle(x)),1)[0]/(2*np.pi))
        raw_leakage_hz = model_hz(true_dc)
        raw_signal_hz = model_hz(true_gain)
        times=np.arange(iq.N)/rate
        extrapolated_dc = dc * np.exp(2j*np.pi*hz*times)
        error = abs(extrapolated_dc-true_dc)/abs(true_gain)
        model_rows.append({
            'position':slot,'baseline_valid':int(values['baseline'].size>0 and iq.hard(values['baseline'][q.PILOT_LEN:])==expected),
            'pilot_evm_pct':100*evm,'pilot_cfo_hz':hz,'data_aided_signal_hz':raw_signal_hz,
            'data_aided_leakage_hz':raw_leakage_hz,
            'pilot_cfo_error_hz':hz-raw_signal_hz,
            'raw_leakage_relative_dbc':20*np.log10(np.median(abs(true_dc)/abs(true_gain))),
            'baseline_leakage_error_mid':error[iq.N//2],'baseline_leakage_error_end':np.median(error[-100:]),
        })
    out.mkdir(parents=True,exist_ok=True)
    iq.write_csv(out/'ablation.csv',rows)
    if model_rows:
        iq.write_csv(out/'data-aided-model.csv',model_rows)
    for mode in values:
        selected = [r for r in rows if r['mode']==mode]
        print(cache.stem, mode, sum(r['valid'] for r in selected),sum(r['bit_errors'] for r in selected),
              'wrong_payload_crc',sum(r['crc_ok'] and not r['valid'] for r in selected))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache',type=Path)
    parser.add_argument('payload_seed',type=int)
    parser.add_argument('order_seed',type=int)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    replay(args.cache,args.payload_seed,args.order_seed,args.out)
