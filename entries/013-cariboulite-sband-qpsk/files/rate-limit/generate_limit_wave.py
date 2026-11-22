"""Build arbitrary QPSK baud rates at integer CaribouLite IQ rates."""
import argparse
from math import gcd
from pathlib import Path
import hashlib
import json

import numpy as np
from scipy import signal

import qpsk_bench_shuffled as q


def generate(path, baud, sample_rate, frames, seed, order_seed):
    if baud*(1+q.BETA)>sample_rate:
        raise ValueError('the nominal RRC occupied band exceeds the complex IQ rate')
    payloads=np.random.default_rng(seed).integers(0,256,(frames,q.PAYLOAD),dtype=np.uint8)
    order=np.random.default_rng(order_seed).permutation(frames)
    symbols=np.empty((frames,q.FRAME_SYMBOLS),np.complex64)
    symbols[:,:q.TONE]=(1+1j)/np.sqrt(2)
    symbols[:,q.TONE:q.TONE+q.PILOT_LEN]=q.PILOT
    for row, seq in zip(symbols,order):
        bits=np.unpackbits(np.frombuffer(q.frame(seq,payloads),dtype=np.uint8))
        row[q.TONE+q.PILOT_LEN:]=q.qpsk(bits)

    intermediate=4*baud
    if sample_rate==2*baud:
        waveform=signal.upfirdn(q.rrc(2),symbols.ravel(),up=2)
    else:
        waveform=signal.upfirdn(q.rrc(4),symbols.ravel(),up=4)
        g=gcd(intermediate,sample_rate)
        waveform=signal.resample_poly(waveform,sample_rate//g,intermediate//g,window=('kaiser',8.0))
    amplitude=float(np.sqrt(np.mean(abs(waveform)**2)))
    waveform *= 12000/amplitude
    lead=sample_rate//5
    usable=len(waveform)
    total=lead*2+usable
    pad=(-total)%q.DMA_SAMPLES
    with path.open('wb') as out:
        out.write(bytes(lead*4))
        for k in range(0,usable,262144):
            z=waveform[k:k+262144]
            values=np.rint(np.column_stack((z.real,z.imag)))
            if np.max(abs(values))>24000:
                raise ValueError('unexpected waveform peak')
            out.write(values.astype('<i2').tobytes())
        out.write(bytes((lead+pad)*4))
    print(json.dumps({'baud':baud,'tx_sample_rate':sample_rate,'frames':frames,'payload_seed':seed,
                      'order_seed':order_seed,'payload_bits_per_frame':4096,'rrc_rolloff':q.BETA,
                      'nominal_bandwidth_hz':baud*(1+q.BETA),'rf_packet_train_seconds':frames*q.FRAME_SYMBOLS/baud,
                      'iq_file_samples':total+pad,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baud',type=int)
    p.add_argument('path',type=Path)
    p.add_argument('--sample-rate',type=int,default=2000000)
    p.add_argument('--frames',type=int,default=256)
    p.add_argument('--seed',type=int,default=225201)
    p.add_argument('--order-seed',type=int,default=225301)
    args=p.parse_args()
    generate(args.path,args.baud,args.sample_rate,args.frames,args.seed,args.order_seed)
