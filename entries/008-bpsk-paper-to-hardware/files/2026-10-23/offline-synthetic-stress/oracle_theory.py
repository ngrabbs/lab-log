"""Known-channel geometry reference, derived separately from frozen decisions."""
import csv,gzip,json,math
import numpy as np
from model_test import *

def main():
 rows=[json.loads(x) for x in gzip.open(HERE/'detector-trials.jsonl.gz','rt')];groups={}
 d2=float(abs(MU[1]-MU[0])**2)
 for row in rows:
    _,_,_,h,_=make_case(row['pattern'],row['profile'],row['ebn0_db'],row['seed'],'detector',row['trial'])
    gamma=10**(row['ebn0_db']/10)
    # Equal-variance nearest-state coherent error probability, with true h.
    p=np.array([.5*math.erfc(math.sqrt(d2*gamma*abs(v)**2/4)) for v in h])
    per_bit=p[PAYLOAD]+p[PAYLOAD-1]-2*p[PAYLOAD]*p[PAYLOAD-1]
    key=(row['profile'],row['ebn0_db']);g=groups.setdefault(key,[0.,0,0])
    g[0]+=float(per_bit.sum());g[1]+=304;g[2]+=row['metrics']['oracle_channel']['payload_errors']
 result=[dict(profile=k[0],ebn0_db=k[1],bits=v[1],predicted_oracle_errors=v[0],observed_oracle_errors=v[2],
    predicted_oracle_data_ber=v[0]/v[1],observed_oracle_data_ber=v[2]/v[1],
    geometry_distance_factor=d2/4,geometry_distance_cost_db=-10*math.log10(d2/4)) for k,v in groups.items()]
 with (HERE/'oracle-theory.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
 print('oracle theory complete',len(result))
if __name__=='__main__':main()
