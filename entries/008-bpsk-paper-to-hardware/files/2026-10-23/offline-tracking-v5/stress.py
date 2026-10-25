"""Retrospective exact replay of the pre-existing frozen stress inputs."""
from pathlib import Path
import importlib.util,json,gzip,hashlib,sys,time
import numpy as np
import receiver as r
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'offline-synthetic-stress'
spec=importlib.util.spec_from_file_location('stress_model',OLD/'model_test.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
M=json.loads((HERE/'model.json').read_text())
def check():
 lock=json.loads((HERE/'selection.json').read_text())
 for relative,digest in lock['dependencies'].items():assert hashlib.sha256((HERE/relative).read_bytes()).hexdigest()==digest,relative
 return lock

def main():
 stage=sys.argv[1];assert stage in ['detector','full'];check();count=0;begin=time.monotonic()
 out=HERE/(stage+'-trials.jsonl.gz');assert not out.exists()
 with gzip.open(OLD/(stage+'-trials.jsonl.gz'),'rt') as source,out.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as dest:
  for line in source:
   old=json.loads(line);meta,truth,x,h,gain=s.make_case(old['pattern'],old['profile'],old['ebn0_db'],old['seed'],stage,old['trial'])
   assert meta['native_hex']==old['native_hex'] and meta['rf_sequence']==old['rf_sequence']
   row=dict(**meta,baseline_aligned=old['aligned'],baseline_metrics=old['metrics'],baseline_decisions_hex=old['decisions_hex'])
   outputs={}
   if stage=='full':
    assert meta['input_iq_sha256']==old['input_iq_sha256'];res=r.locate(x,M)
    aligned=bool(res['detected'] and abs(res['start_sample']-meta['true_start_sample'])<=20)
    row.update(acquisition=res,aligned=aligned)
    if res['detected']:z=r.v4.symbols_at(x,res)
   else:aligned=True;row['aligned']=True;z=x
   if stage=='detector' or res['detected']:
    outputs['tracked'],info=r.detect_symbols(z,M);outputs['preamble_only'],_=r.detect_symbols(z,M,0.)
    row['tracking']=info
   row['metrics']={name:s.metrics(outputs.get(name),truth,aligned) for name in ['tracked','preamble_only']}
   row['decisions_hex']={name:np.packbits(np.maximum(bits,0).astype(np.uint8)).tobytes().hex() for name,bits in outputs.items()}
   dest.write((json.dumps(row,separators=(',',':'))+'\n').encode());count+=1
   if count%60==0:print(stage,count,round(time.monotonic()-begin,1),flush=True)
 check();print('complete',stage,count,flush=True)
if __name__=='__main__':main()
