"""Extract and replay matched-filter symbols from the conducted IQ archives."""
import argparse
import csv
import json
from pathlib import Path
import struct
import zlib

import numpy as np
from scipy import signal

import qpsk_bench_shuffled as q

N = q.PILOT_LEN + q.FRAME_BYTES * 4


def extract_run(rate, path, carrier_hint_hz=None):
    z, clip = q.extract(path)
    offset, stop, _, _, noise = q.active_window(z)
    z = z[offset:stop]
    cfo = q.carrier(z) if carrier_hint_hz is None else carrier_hint_hz
    z *= np.exp(-2j*np.pi*cfo/q.TX_FS*np.arange(len(z))).astype(np.complex64)
    sps = q.TX_FS // rate
    z = signal.fftconvolve(z, q.rrc(sps), mode='same')
    conjugated, data, correlation, peaks = q.correlate(z, sps)
    peaks = peaks[(peaks>0)&(peaks<len(correlation)-1)]
    left, middle, right = correlation[peaks-1], correlation[peaks], correlation[peaks+1]
    starts = peaks + (.5*(left-right)/(left-2*middle+right)).clip(-.6,.6)
    assert len(starts) == q.FRAMES
    spacing = q.estimate_spacing(starts,q.FRAME_SYMBOLS*sps,sps)
    indices = starts[:, None] + spacing * np.arange(N)
    grid = np.arange(len(data))
    symbols = np.interp(indices, grid, data.real) + 1j*np.interp(indices, grid,data.imag)
    return {
        'symbols':symbols.astype(np.complex64), 'starts_s':(starts+offset)/q.TX_FS,
        'spacing':spacing, 'rate':rate, 'noise':noise, 'cfo':cfo, 'clip':clip,
        'conjugated':conjugated,
    }


def hard(value):
    return np.packbits(np.column_stack([value.real,value.imag]).ravel()<0).tobytes()


def crc_ok(packet):
    return zlib.crc32(packet[:-4]) == struct.unpack_from('<I', packet,len(packet)-4)[0]


def baseline(samples, rate):
    cal, evm = q.phase_track(samples[:q.PILOT_LEN], rate)
    value = q.equalize(samples, np.arange(len(samples)), rate, cal)
    return q.track_payload_phase(value), cal, evm


def expected_bytes(payload_seed, order_seed):
    payloads = q.science_payloads(payload_seed)
    return [q.frame(seq, payloads) for seq in q.sequence_order(order_seed)]


def per_symbol_errors(observed, expected):
    diff = np.frombuffer(observed,dtype=np.uint8)^np.frombuffer(expected,dtype=np.uint8)
    return np.unpackbits(diff).reshape(-1,2).sum(axis=1)


def investigate(path, payload_seed, order_seed, out):
    archive = np.load(path)
    rate = int(archive['rate'])
    rows = []
    errors = []
    ref = expected_bytes(payload_seed,order_seed)
    values = []
    gain = []
    pilot_calibrated = []
    for i, (samples, expected) in enumerate(zip(archive['symbols'],ref)):
        v, calib, evm = baseline(samples,rate)
        packet = hard(v[q.PILOT_LEN:])
        e = per_symbol_errors(packet,expected)
        hz, a, b, d = calib
        c = q.qpsk(np.unpackbits(np.frombuffer(expected,dtype=np.uint8)))
        ratio = v[q.PILOT_LEN:]*c.conj()
        err_idx = np.flatnonzero(e)
        rows.append({'position':i,'valid':int(crc_ok(packet) and packet==expected),'errors':int(e.sum()),
                     'first_error':int(err_idx[0]) if err_idx.size else '',
                     'last_error':int(err_idx[-1]) if err_idx.size else '',
                     'pilot_evm_pct':100*evm,'pilot_residual_hz':hz,
                     'image_dbc':20*np.log10(abs(b)/abs(a)),
                     'carrier_dbc':20*np.log10(abs(d)/abs(a)),
                     'payload_evm_pct':100*np.sqrt(np.mean(abs(ratio-1)**2)),
                     'max_129sym_phase_deviation_deg':np.max(abs(np.angle(signal.convolve(ratio,np.hanning(129)/64,mode='valid'),deg=True))),
                     'min_payload_symbol_magnitude':abs(v[q.PILOT_LEN:]).min()})
        values.append(v)
        gain.append([hz,a,b,d])
        errors.append(e)
        pilot_calibrated.append(q.equalize(samples, np.arange(N),rate,calib))
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'baseline-diagnostics.csv',rows)
    np.savez_compressed(out/'baseline-symbols.npz',errors=errors, values=values, calibration=gain, pilot_calibrated=pilot_calibrated)
    print(path.stem, sum(r['valid'] for r in rows), sum(r['errors'] for r in rows))


def write_csv(path,rows):
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    ext=sub.add_parser('extract')
    ext.add_argument('rate',type=int)
    ext.add_argument('iq',type=Path)
    ext.add_argument('symbols',type=Path)
    ext.add_argument('--carrier-hint-hz', type=float, help='coarse carrier offset after the nominal 500 kHz RX translation')
    study=sub.add_parser('baseline')
    study.add_argument('symbols',type=Path)
    study.add_argument('payload_seed',type=int)
    study.add_argument('order_seed',type=int)
    study.add_argument('out',type=Path)
    args=p.parse_args()
    if args.action=='extract':
        np.savez(args.symbols, **extract_run(args.rate,args.iq,args.carrier_hint_hz))
    else:
        investigate(args.symbols,args.payload_seed,args.order_seed,args.out)
