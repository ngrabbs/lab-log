"""Plot measured preamble states from three published CSVs; no device access."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
here=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
fig,axes=plt.subplots(1,3,figsize=(13,5),layout='constrained')
fig.suptitle('Independent receiver cross-check: the non-antipodal phase alphabet repeats\nSame transceiver and DC-block/pad chain | 437 MHz tuning | 1200 symbols/s',fontsize=14)
rowspec=[('LibreSDR capture 1','iq-heartbeat-01-preamble.csv',json.loads((here/'iq-heartbeat-01-session.json').read_text())['preamble_frequency_refinement']['separation_deg']),('LibreSDR capture 2','iq-heartbeat-02-preamble.csv',json.loads((here/'iq-heartbeat-02-session.json').read_text())['analysis']['channels'][0]['phase']['refinement']['separation_deg']),('Pluto capture 1','iq-pluto-01-preamble-193tap.csv',json.loads((here/'iq-pluto-01-session.json').read_text())['analysis']['filters'][0]['phase']['refinement']['separation_deg'])]
for ax,(label,filename,expected) in zip(axes,rowspec):
 with (here/filename).open() as f:rows=list(csv.DictReader(f))
 states=np.array([int(r['state']) for r in rows]);times=np.array([int(r['preamble_symbol_index'])/1200 for r in rows]);coarse=np.array([complex(float(r['coarse_cfo_real']),float(r['coarse_cfo_imag'])) for r in rows])
 mu=np.array([coarse[states==s].mean() for s in (0,1)])
 slope,_=np.polyfit(times,np.unwrap(np.angle(coarse*np.conj(mu[states]))),1)
 points=coarse*np.exp(-1j*slope*times)
 exported=np.array([complex(float(r['refined_cfo_real']),float(r['refined_cfo_imag'])) for r in rows]);assert np.allclose(points,exported,rtol=1e-10,atol=1e-12)
 centers=np.array([points[states==s].mean() for s in (0,1)]);sep=abs(np.angle(centers[1]*centers[0].conjugate()))*180/np.pi;assert abs(sep-expected)<1e-9
 factor=np.exp(-1j*np.angle(centers[0]))/abs(centers[0]);points*=factor;centers*=factor
 theta=np.linspace(0,2*np.pi,300);ax.plot(np.cos(theta),np.sin(theta),color='#cbd5e1',lw=1)
 for s,color in [(0,'#1d4ed8'),(1,'#b45309')]:
  v=points[states==s];ax.scatter(v.real,v.imag,s=12,alpha=.6,color=color,label=f'State {s}');ax.plot([0,centers[s].real],[0,centers[s].imag],color=color);ax.scatter([centers[s].real],[centers[s].imag],marker='x',s=75,color='#111827')
 ax.scatter([-1],[0],marker='+',s=85,color='#64748b',label='Ideal 180° state');ax.set(title=f'{label}: {sep:.2f}°',xlabel='Normalized I',ylabel='Normalized Q',xlim=(-1.4,1.4),ylim=(-1.4,1.4),aspect='equal');ax.grid(alpha=.15)
axes[0].legend(loc='upper right',fontsize=8)
fig.supxlabel('248 known preamble symbols; central 8/40 samples after resampling to 48 ksample/s; one common frequency refinement.\nEach panel has one global rotation/scale. Pluto: low ADC code excursion; different analog/FPGA filters. These are not calibrated phase or BER results.',fontsize=9)
dest=here.parents[1]/'images';fig.savefig(dest/'iq-pluto-comparison.svg');fig.savefig(dest/'iq-pluto-comparison.png',dpi=150)
