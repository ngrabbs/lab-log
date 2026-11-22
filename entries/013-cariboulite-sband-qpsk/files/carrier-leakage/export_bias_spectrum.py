"""Export aligned spectra from the interleaved bias-validation capture."""
import argparse
import csv
from pathlib import Path
import numpy as np

from analyze_probe import FS, line, spectra
from bias_probe import DURATION, RF_TONE, get_anchor


def export(path,out):
    raw, anchor=get_anchor(path,[(0,0),(128,-4280),(0,0),(128,-4280)])
    frequency=np.arange(-270_000,70_001,125)
    levels=[]
    for k in range(4):
        f,p=spectra(raw,round((anchor+k*DURATION+.03)*FS),
                    round((anchor+(k+1)*DURATION-.03)*FS),65536)
        tone,_=line(f,p,RF_TONE,65000)
        levels.append(np.interp(frequency,f-tone-200000,p.mean(axis=0)/(127**2)))
    compare=[10*np.log10((levels[i]+levels[i+2])/2) for i in (0,1)]
    with out.open('w',newline='') as handle:
        writer=csv.writer(handle,lineterminator='\n')
        writer.writerow(['frequency_from_carrier_hz','reference_dbfs_per_bin','bias_dbfs_per_bin'])
        writer.writerows(zip(frequency,*compare))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    export(args.capture,args.output)
