"""Reproduce two-capture phase comparison from published CSV/JSON; no device access."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
here=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
fig,axes=plt.subplots(1,3,figsize=(14,5),layout='constrained')
fig.suptitle('Conducted heartbeat repeat: phase alphabet persists\n437 MHz tuning | 1200 symbols/s | same pads, DC block, receiver gain and bandwidth',fontsize=14)
for i in (1,2):
 meta=json.loads((here/f'iq-heartbeat-0{i}-session.json').read_text())
 phase=meta['preamble_frequency_refinement'] if i==1 else meta['analysis']['channels'][0]['phase']['refinement']
 with (here/f'iq-heartbeat-0{i}-preamble.csv').open() as f:rows=list(csv.DictReader(f))
 coarse=np.array([complex(float(r['coarse_cfo_real']),float(r['coarse_cfo_imag'])) for r in rows]);states=np.array([int(r['state']) for r in rows]);times=np.array([int(r['preamble_symbol_index'])/1200 for r in rows])
 centers=np.array([coarse[states==s].mean() for s in (0,1)])
 slope,_=np.polyfit(times,np.unwrap(np.angle(coarse*np.conj(centers[states]))),1)
 points=coarse*np.exp(-1j*slope*times)
 exported=np.array([complex(float(r['refined_cfo_real']),float(r['refined_cfo_imag'])) for r in rows])
 assert np.allclose(points,exported,rtol=1e-10,atol=1e-12)
 centers=np.array([points[states==s].mean() for s in (0,1)])
 separation=abs(np.angle(centers[1]*centers[0].conjugate()))*180/np.pi
 assert abs(separation-phase['separation_deg'])<1e-9
 factor=np.exp(-1j*np.angle(centers[0]))/abs(centers[0]);points*=factor;centers*=factor
 ax=axes[i-1];theta=np.linspace(0,2*np.pi,300);ax.plot(np.cos(theta),np.sin(theta),color='#cbd5e1',lw=1)
 for s,color in [(0,'#1d4ed8'),(1,'#b45309')]:
  v=points[states==s];ax.scatter(v.real,v.imag,s=11,alpha=.55,color=color,label=f'State {s}');ax.plot([0,centers[s].real],[0,centers[s].imag],color=color);ax.scatter([centers[s].real],[centers[s].imag],marker='x',s=75,color='#111827')
 ax.scatter([-1],[0],marker='+',s=85,color='#64748b',label='Ideal 180° state')
 ax.set(title=f'Capture {i}: {separation:.2f}°',xlabel='Normalized I',ylabel='Normalized Q',xlim=(-1.4,1.4),ylim=(-1.4,1.4),aspect='equal');ax.grid(alpha=.15)
 if i==1:ax.legend(loc='upper right',fontsize=8)
 with (here/f'iq-heartbeat-0{i}-power.csv').open() as f:rows=list(csv.DictReader(f))
 t=np.array([float(r['seconds_from_capture_start']) for r in rows]);p=np.array([float(r['ch0_mean_iq_power']) for r in rows]);t-=t[np.argmax(p)]
 axes[2].plot(t,10*np.log10(p),label=f'Capture {i}',alpha=.8)
axes[2].set(title='Dominant RXA / channel-0 path',xlabel='Time relative to peak 10 ms block (s)',ylabel='10 log10(mean |IQ|²), digital units',xlim=(-.65,.65));axes[2].grid(alpha=.2);axes[2].legend()
fig.supxlabel('248 known preamble symbols per capture; central 8/40 samples; one common frequency refinement, then global rotation/scale.\nTwo captures, no BER inference. Timing sensitivity exceeds the precision of the displayed center estimates.',fontsize=9)
dest=here.parents[1]/'images';fig.savefig(dest/'iq-heartbeat-repeat.svg');fig.savefig(dest/'iq-heartbeat-repeat.png',dpi=150)
