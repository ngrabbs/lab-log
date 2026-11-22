"""Add a measured constant TX I/Q correction with a clipping check."""
import argparse
import json
from pathlib import Path

import numpy as np


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('bias_i',type=int)
    parser.add_argument('bias_q',type=int)
    args=parser.parse_args()
    raw=np.fromfile(args.input,dtype='<i2').reshape(-1,2)
    corrected=raw.astype(np.int32)+[args.bias_i,args.bias_q]
    if corrected.min() < -32768 or corrected.max() > 32767:
        raise ValueError('TX sample bias would clip the waveform')
    corrected.astype('<i2').tofile(args.output)
    print(json.dumps({'bias_i':args.bias_i,'bias_q':args.bias_q,'samples':len(raw),
                      'min_iq':corrected.min(axis=0).tolist(),'max_iq':corrected.max(axis=0).tolist()}))
