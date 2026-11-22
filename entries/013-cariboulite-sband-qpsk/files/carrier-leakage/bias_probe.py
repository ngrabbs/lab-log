"""Generate and measure a two-axis TX sample-bias grid downstream of calibration."""
import argparse
from pathlib import Path
import csv
import json

import numpy as np

from analyze_probe import FS, line, spectra

TX_FS = 2_000_000
RF_TONE = 300_000  # Inverted +200 kHz digital tone with a 500 kHz RX offset.
BLOCK = 262144
DURATION = BLOCK / TX_FS
GRID = [(0,0),(-6000,0),(6000,6000),(0,-6000),(-6000,6000),(6000,0),
        (-6000,-6000),(0,6000),(6000,-6000),(0,0)]


def generate(path, offsets):
    n = np.arange(BLOCK)
    tone = np.exp(2j*np.pi*.1*n)*12000
    base = np.rint(np.column_stack((tone.real,tone.imag))).astype('<i2')
    zero = np.zeros_like(base)
    np.concatenate([zero,*[base+np.array(d,dtype='<i2') for d in offsets],zero]).tofile(path)


def get_anchor(path, offsets):
    raw=np.memmap(path,dtype=np.int8,mode='r').reshape(-1,2)
    n=16384
    levels=[]
    for a in range(0,len(raw)-n+1,128*n):
        f,p=spectra(raw,a,min(len(raw),a+128*n),n)
        levels.extend(np.max(p[:,abs(f-RF_TONE)<65000],axis=1))
    levels=np.array(levels)
    mask=levels>max(100*np.median(levels), .12*np.max(levels))
    intervals=np.flatnonzero(np.diff(np.r_[False,mask,False])).reshape(-1,2)
    first,last=max(intervals,key=lambda v:v[1]-v[0])
    assert abs((last-first)*n/FS-len(offsets)*DURATION)<.025
    anchor=(first+.5)*n/FS
    return raw, anchor


def measure(path, offsets, out):
    raw, anchor = get_anchor(path, offsets)
    rows=[]
    for index,(di,dq) in enumerate(offsets):
        f,p=spectra(raw,round((anchor+index*DURATION+.026)*FS),
                    round((anchor+(index+1)*DURATION-.026)*FS),65536)
        ref,level=line(f,p,RF_TONE,65000)
        freq,carrier=line(f,p,ref+200000,600)
        rows.append({'index':index,'bias_i':di,'bias_q':dq,'tone_dbfs':level,
                     'carrier_dbfs':carrier,'carrier_dbc':carrier-level,'carrier_rx_offset_hz':freq})
    with out.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    if len(rows)>=9:
        u,v=np.array(offsets,dtype=float).T/6000
        design=np.column_stack((u*u,2*u*v,v*v,2*u,2*v,np.ones(len(u))))
        c=np.linalg.lstsq(design,10**(np.array([r['carrier_dbc'] for r in rows])/10),rcond=None)[0]
        h=np.array([[c[0],c[1]],[c[1],c[2]]])
        fit=6000*np.linalg.solve(h,-c[3:5])
        assert np.all(np.linalg.eigvalsh(h)>0) and np.max(abs(fit))<7500
        bias=(8*np.rint(fit/8)).astype(int).tolist()
        print(json.dumps({'fit_counts':fit.tolist(),'rounded_counts':bias,'coefficients':c.tolist(),
                          'max_abs_power_residual':float(np.max(abs(design@c-10**(np.array([r['carrier_dbc'] for r in rows])/10))))}))
    for row in rows:
        print(row['bias_i'],row['bias_q'],round(row['carrier_dbc'],2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('generate','measure'))
    parser.add_argument('path',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--offsets',type=Path)
    args=parser.parse_args()
    offsets=json.loads(args.offsets.read_text()) if args.offsets else GRID
    if args.mode=='generate':
        generate(args.path,offsets)
    else:
        measure(args.path,offsets,args.output)
