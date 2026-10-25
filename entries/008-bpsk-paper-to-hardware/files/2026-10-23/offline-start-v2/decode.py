"""Blind offline CLI: no manifest, expected timing/CFO, or body reference."""
import argparse,json
from pathlib import Path
import numpy as np
from receiver import acquire
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('iq',type=Path,help='NPY samples or NPZ with iq array; 48000 complex samples/s')
p.add_argument('--model',type=Path,default=Path(__file__).with_name('model.json'))
a=p.parse_args();x=np.load(a.iq,allow_pickle=False)
if isinstance(x,np.lib.npyio.NpzFile):x=x['iq']
r=acquire(x,json.loads(a.model.read_text()))
if 'bits' in r:
    bits=r.pop('bits');r['decisions_hex']=np.packbits(np.maximum(bits,0).astype(np.uint8)).tobytes().hex()
    r['unobserved_bit_indices']=[0]
print(json.dumps(r,indent=2))
