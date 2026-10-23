"""Paper phase-2 ideal controls: Ns=8, symbol-center phase oracle, Eb=1.
This isolates rectangular-integration loss; it is not preamble acquisition.
"""
import math,json,csv
import numpy as np
from model_test import HERE

def q(x):return .5*math.erfc(x/math.sqrt(2))
def main():
 rows=[]
 for eb in [4,8,12]:
  gamma=10**(eb/10)
  for nu in [0.,.10]:
   h=np.mean(np.exp(2j*np.pi*nu*np.arange(8)/8));amp=abs(h)
   p=q(math.sqrt(2*gamma)*amp)
   counts={name:[] for name in ['coherent_state','coherent_xor_data','dbpsk_data']}
   for trial in range(250):
    rng=np.random.default_rng(np.random.SeedSequence([91001,eb,int(nu*1000),trial]))
    bits=rng.integers(0,2,1001);states=np.cumsum(bits)%2
    z=amp*(1-2*states)+(rng.normal(size=1001)+1j*rng.normal(size=1001))/math.sqrt(2*gamma)
    phase=(z.real<0).astype(np.uint8)
    decisions=(np.real(z[1:]*z[:-1].conj())<0).astype(np.uint8)
    counts['coherent_state'].append(int(np.sum(phase[1:]!=states[1:])))
    counts['coherent_xor_data'].append(int(np.sum((phase[1:]^phase[:-1])!=bits[1:])))
    counts['dbpsk_data'].append(int(np.sum(decisions!=bits[1:])))
   theory=dict(coherent_state=p,coherent_xor_data=2*p*(1-p),dbpsk_data=.5*math.exp(-gamma*amp*amp))
   for name,c in counts.items():
    rows.append(dict(ebn0_db=eb,nu=nu,detector=name,bits=250000,errors=sum(c),ber=sum(c)/250000,
      theory_discrete_ns8=theory[name],continuous_sinc2_gain=float(np.sinc(nu)**2),discrete_gain=amp*amp,
      trial_count=250,bits_per_trial=1000,trial_ber_standard_error=float(np.std(np.array(c)/1000,ddof=1)/math.sqrt(250))))
 with (HERE/'paper-control.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (HERE/'paper-control-counts.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('paper control complete',len(rows),'summary rows')
if __name__=='__main__':main()
