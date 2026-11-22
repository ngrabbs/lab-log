"""Decode a rate-sweep capture using known pilots and verify its payload after slicing."""
import argparse
import csv
import json
from math import gcd
from pathlib import Path
import struct
import zlib

import numpy as np
from scipy import signal

import qpsk_bench_shuffled as q


SPS = 4
COARSE_HZ = 22100
N = q.PILOT_LEN + q.FRAME_BYTES * 4


def matched_filter(path, baud, rx_offset):
    q.RX_OFFSET = rx_offset
    z, clip = q.extract(path)
    a,b,start,stop,noise=q.active_window(z)
    z=z[a:b]
    z *= np.exp(-2j*np.pi*COARSE_HZ/q.TX_FS*np.arange(len(z))).astype(np.complex64)
    fs = SPS*baud
    g = gcd(q.TX_FS,fs)
    z = signal.resample_poly(z,fs//g,q.TX_FS//g,window=('kaiser',8))
    return signal.fftconvolve(z,q.rrc(SPS),mode='same'), a/q.TX_FS, clip, start,stop


def acquire(matched, frames):
    impulse=np.zeros((q.PILOT_LEN-1)*SPS+1,np.complex64)
    impulse[::SPS] = q.PILOT
    step=q.FRAME_SYMBOLS*SPS
    best=None
    for conjugated in (False,True):
        data=matched.conj() if conjugated else matched
        corr=abs(signal.fftconvolve(data,impulse[::-1].conj(),mode='valid'))
        peaks,_=signal.find_peaks(corr,height=.32*float(np.max(corr)),distance=int(.84*step))
        strength=np.sum(np.sort(corr[peaks])[-frames:])
        if best is None or strength>best[0]:
            best=strength, conjugated, corr, peaks
    _, conjugated, corr, peaks=best
    # Find the shared frame lattice, allowing missed pilots and rejecting false peaks.
    left, mid, right=corr[peaks-1],corr[peaks],corr[peaks+1]
    raw=peaks+(.5*(left-right)/(left-2*mid+right)).clip(-.6,.6)
    spacing0=q.estimate_spacing(raw,step,SPS)*q.FRAME_SYMBOLS
    idx=np.rint((raw-raw[0])/spacing0).astype(int)
    position=np.polyfit(idx,raw,1)
    # A real pilot lands close to its slot even if a low peak appears between bursts.
    valid=abs(raw-np.polyval(position,idx))<max(2,step*.015)
    if weighted:=int(np.count_nonzero(valid)):
        if weighted>=2:
            position=np.polyfit(idx[valid],raw[valid],1)
    selected=raw[valid]
    if len(selected)>frames:
        raise ValueError(f'pilot lattice ambiguous: {len(selected)} detections for {frames} frames')
    return matched.conj() if conjugated else matched,selected,float(position[0])/q.FRAME_SYMBOLS,conjugated


def leakage_and_phase(samples, rate):
    calibration,_=q.phase_track(samples[:q.PILOT_LEN],rate)
    hz,a,b,d=calibration
    corrected=samples.copy()
    n=np.arange(q.PILOT_LEN)
    corrected[:q.PILOT_LEN] -= (a*q.PILOT+b*q.PILOT.conj())*np.exp(2j*np.pi*hz*n/rate)
    win=np.hanning(385)
    d=signal.convolve(corrected,win,mode='same')/signal.convolve(np.ones(len(samples)),win,mode='same')
    return q.track_payload_phase((samples-d)/a)


def pilot_equalizer(value):
    # Only the public preamble trains the filter, with 24 pilot symbols reserved for EVM.
    taps=7
    margin=taps//2
    windows=np.lib.stride_tricks.sliding_window_view(np.pad(value,margin),taps)
    x=windows[8:104]
    target=q.PILOT[8:104]
    normal=x.conj().T@x + .018*np.eye(taps)
    coeff=np.linalg.solve(normal,x.conj().T@target)
    return windows@coeff


def payload(value, expected):
    bits=np.column_stack([value.real,value.imag]).ravel()<0
    packet=np.packbits(bits).tobytes()
    crc=zlib.crc32(packet[:-4])==struct.unpack_from('<I',packet,len(packet)-4)[0]
    seq=struct.unpack_from('<I',packet)[0]
    valid=crc and seq<len(expected) and packet==expected[seq]
    return seq,valid,crc


def decode(path,meta,rx_offset,out):
    baud,frames=meta['baud'],meta['frames']
    expected_payload=np.random.default_rng(meta['payload_seed']).integers(0,256,(frames,q.PAYLOAD),dtype=np.uint8)
    expected=[q.frame(i, expected_payload) for i in range(frames)]
    matched, origin, clip, rf_start, rf_stop=matched_filter(path,baud,rx_offset)
    data,starts,sps,conjugated=acquire(matched,frames)
    rows=[]
    accepted={'tracked':set(),'equalized':set()}
    pos=np.arange(N)
    for peak in starts:
        indices=peak+sps*pos
        a,b=int(indices[0])-1,int(indices[-1])+3
        if a<0 or b>len(data):
            continue
        z=data[a:b]
        grid=np.arange(len(z))
        samples=np.interp(indices-a,grid,z.real)+1j*np.interp(indices-a,grid,z.imag)
        if np.max(abs(samples[:q.PILOT_LEN]))<1e-5:
            continue
        tracked=leakage_and_phase(samples,baud)
        equalized=pilot_equalizer(tracked)
        row={'pilot_start_s':origin+peak/(SPS*baud)}
        for label,value in (('tracked',tracked),('equalized',equalized)):
            seq,valid,crc=payload(value[q.PILOT_LEN:],expected)
            row[f'{label}_seq']=seq
            row[f'{label}_valid']=int(valid)
            row[f'{label}_crc']=int(crc)
            row[f'{label}_held_pilot_evm_pct']=100*np.sqrt(np.mean(abs(value[104:q.PILOT_LEN]-q.PILOT[104:])**2))
            if valid:
                accepted[label].add(seq)
        rows.append(row)
    duration=frames*q.FRAME_SYMBOLS/baud
    result={'baud':baud,'tx_sample_rate':meta['tx_sample_rate'],'expected_frames':frames,'preambles':len(rows),
            'adc_component_clip_fraction':float(clip),'effective_sps':sps,'conjugated':conjugated,
            'rf_gate_s':rf_stop-rf_start,'packet_train_s':duration}
    for label,observed in accepted.items():
        values=[r[f'{label}_held_pilot_evm_pct'] for r in rows]
        result[f'{label}_frames']=len(observed)
        result[f'{label}_goodput_bps']=len(observed)*4096/duration
        result[f'{label}_median_held_pilot_evm_pct']=float(np.median(values)) if values else None
    if rows:
        with (out/'detections.csv').open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('iq',type=Path)
    p.add_argument('waveform',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--rx-offset-hz',type=int,default=150000)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    decode(args.iq,json.loads(args.waveform.read_text()),args.rx_offset_hz,args.out)
