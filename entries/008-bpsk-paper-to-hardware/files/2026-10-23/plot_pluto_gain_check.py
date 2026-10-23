"""Reproduce Pluto gain-check plot from published measurements; no device access."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
here=Path(__file__).resolve().parent
meta=json.loads((here/'iq-pluto-gain20-01-session.json').read_text())
base=json.loads((here/'iq-pluto-01-session.json').read_text())
plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
fig,axes=plt.subplots(1,3,figsize=(13,5),layout='constrained')
fig.suptitle('Pluto receive-gain check: more ADC signal, similar phase separation\nSame transceiver, RF chain, tuning, rates and filters | one heartbeat per gain setting',fontsize=14)
for ax,label,name,expected in [(axes[0],'Manual gain 0 dB','iq-pluto-01-preamble-193tap.csv',base['analysis']['filters'][0]['phase']['refinement']['separation_deg']),(axes[1],'Manual gain 20 dB','iq-pluto-gain20-01-preamble-193tap.csv',meta['analysis']['filters'][0]['phase']['refinement']['separation_deg'])]:
 with (here/name).open() as f:rows=list(csv.DictReader(f))
 s=np.array([int(r['state']) for r in rows]);t=np.array([int(r['preamble_symbol_index'])/1200 for r in rows]);coarse=np.array([complex(float(r['coarse_cfo_real']),float(r['coarse_cfo_imag'])) for r in rows]);mu=np.array([coarse[s==k].mean() for k in (0,1)])
 slope,_=np.polyfit(t,np.unwrap(np.angle(coarse*np.conj(mu[s]))),1);v=coarse*np.exp(-1j*slope*t)
 exported=np.array([complex(float(r['refined_cfo_real']),float(r['refined_cfo_imag'])) for r in rows]);assert np.allclose(v,exported,rtol=1e-10,atol=1e-12)
 centers=np.array([v[s==k].mean() for k in (0,1)]);sep=abs(np.angle(centers[1]*centers[0].conjugate()))*180/np.pi;assert abs(sep-expected)<1e-9
 factor=np.exp(-1j*np.angle(centers[0]))/abs(centers[0]);v*=factor;centers*=factor
 theta=np.linspace(0,2*np.pi,300);ax.plot(np.cos(theta),np.sin(theta),color='#cbd5e1',lw=1)
 for k,color in [(0,'#1d4ed8'),(1,'#b45309')]:
  p=v[s==k];ax.scatter(p.real,p.imag,s=12,alpha=.6,color=color,label=f'State {k}');ax.plot([0,centers[k].real],[0,centers[k].imag],color=color);ax.scatter([centers[k].real],[centers[k].imag],marker='x',s=75,color='#111827')
 ax.scatter([-1],[0],marker='+',s=85,color='#64748b',label='Ideal 180° state');ax.set(title=f'{label}: {sep:.2f}°',xlabel='Normalized I',ylabel='Normalized Q',xlim=(-1.4,1.4),ylim=(-1.4,1.4),aspect='equal');ax.grid(alpha=.15)
axes[0].legend(loc='upper right',fontsize=8)
counts=[base['capture']['peak_abs_component'],meta['capture']['peak_abs_component']]
axes[2].bar(['0 dB gain','20 dB gain'],counts,color=['#64748b','#1d4ed8'],width=.55)
for i,c in enumerate(counts):axes[2].text(i,c+7,f'{c} counts\n{100*c/2048:.2f}% full scale',ha='center')
axes[2].set(title='Peak absolute raw I/Q component',ylabel='ADC-format counts (nominal full scale = 2048)',ylim=(0,285));axes[2].grid(axis='y',alpha=.2)
fig.supxlabel('Phase: 248 known preamble symbols, central 8/40 samples; one common frequency refinement and global rotation/scale.\nNo per-symbol correction. One capture at each gain; timing sensitivity exceeds the 0.36° difference. No BER or calibrated SNR inferred.',fontsize=9)
dest=here.parents[1]/'images';fig.savefig(dest/'iq-pluto-gain-check.svg');fig.savefig(dest/'iq-pluto-gain-check.png',dpi=150)
