"""Fixed synthetic stress budgets, no receiver selection or retuning."""
import argparse,json,gzip,time
from pathlib import Path
import numpy as np
from model_test import *

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['detector','full']);a=p.parse_args()
    frozen=freeze_check();lock=HERE/'frozen-hashes.json'
    if lock.exists():assert json.loads(lock.read_text())==frozen
    else:lock.write_text(json.dumps(frozen,indent=2)+'\n')
    out=HERE/(a.stage+'-trials.jsonl.gz');assert not out.exists(),'Archive prior results before rerunning'
    profiles=PROFILES if a.stage=='detector' else FULL_PROFILES
    seeds=[79001,79002,79003] if a.stage=='detector' else [81001,81002,81003]
    grid=[4,8,12] if a.stage=='detector' else [8,12]
    n=10 if a.stage=='detector' else 3
    cases=[(pattern,profile,eb,seed,trial) for pattern in PATTERNS for profile in profiles for eb in grid for seed in seeds for trial in range(n)]
    if a.stage=='full':cases += [(pattern,profile,'clean',82001,0) for pattern in PATTERNS for profile in profiles]
    begin=time.monotonic();count=0
    with out.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as zipped:
      for pattern,profile,eb,seed,trial in cases:
        meta,truth,x,h,gain=make_case(pattern,profile,eb,seed,a.stage,trial)
        if a.stage=='detector':
            outputs=detectors(x,h,gain);row=dict(**meta,aligned=True,metrics={name:metrics(bits,truth) for name,bits in outputs.items()})
        else:
            result=v4.acquire(x,MODEL);aligned=bool(result['detected'] and abs(result['start_sample']-meta['true_start_sample'])<=20)
            outputs={} if not result['detected'] else dict(sign=decoded(result['sign_decisions_hex']),pair=decoded(result['baseline_decisions_hex']),sequence=result.pop('bits'))
            row=dict(**meta,aligned=aligned,acquisition=result,
                     metrics={name:metrics(outputs.get(name),truth,aligned) for name in ['sign','pair','sequence']})
        row['decisions_hex']={name:np.packbits(np.maximum(bits,0).astype(np.uint8)).tobytes().hex() for name,bits in outputs.items()}
        zipped.write((json.dumps(row,separators=(',',':'))+'\n').encode());count+=1
        if count%30==0:print(a.stage,count,'/',len(cases),'elapsed',round(time.monotonic()-begin,1),flush=True)
    assert freeze_check()==frozen
    print('complete',a.stage,count,flush=True)
if __name__=='__main__':main()
