"""Stress figures calculated from saved counts, not fitted response curves."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
read=lambda name:list(csv.DictReader((HERE/name).open()))
det=read('detector-summary.csv');full=read('full-summary.csv')
plt.rcParams.update({'font.size':9,'svg.fonttype':'none'})
fig,axes=plt.subplots(1,2,figsize=(12,4.6))
profiles=['static','residual002','residual010','ramp100','walk3','walk12']
for j,(method,color,marker,label) in enumerate([('sign','#747d8c','o','Sign'),('pair','#4c78a8','s','Pair'),('sequence','#087f8c','D','Frozen sequence'),('oracle_channel','#222222','^','True-channel oracle')]):
 values=[next(r for r in det if r['pattern']=='ALL' and r['profile']==p and r['ebn0_db']=='8' and r['detector']==method) for p in profiles]
 axes[0].scatter([k+(j-1.5)*.14 for k in range(len(profiles))],[100*float(r['payload_ber']) for r in values],color=color,marker=marker,s=32,label=label)
axes[0].set_yscale('log');axes[0].set_ylabel('Known payload BER (%)');axes[0].set_xticks(range(6),['None','ν=.02','ν=.10','100 Hz/s','3° walk','12° walk'],rotation=18)
axes[0].set_title('Known timing, uncorrected drift · 8 dB');axes[0].legend(fontsize=8,loc='upper left');axes[0].grid(axis='y',which='both',alpha=.2)
profiles=['static','ramp5','ramp100','walk3','walk12']
for j,(eb,color) in enumerate([('8','#747d8c'),('12','#087f8c')]):
 values=[next(r for r in full if r['pattern']=='ALL' and r['profile']==p and r['ebn0_db']==eb and r['detector']=='sequence') for p in profiles]
 xx=[k+(j-.5)*.36 for k in range(5)];yy=[int(r['aligned']) for r in values]
 axes[1].bar(xx,yy,width=.33,label=eb+' dB',color=color)
 for x,y in zip(xx,yy):axes[1].text(x,y-5,str(y),ha='center',color='white',fontweight='bold',fontsize=8)
axes[1].set_ylim(0,60);axes[1].set_xticks(range(5),['Static CFO','5 Hz/s','100 Hz/s','3° walk','12° walk'],rotation=18);axes[1].set_ylabel('Correct acquisitions / 54');axes[1].set_title('Full receiver, unknown timing/CFO');axes[1].legend(loc='lower left');axes[1].grid(axis='y',alpha=.2);axes[1].set_axisbelow(True)
fig.suptitle('Frozen sequence receiver: synthetic payload and drift stress',fontsize=12)
fig.text(.5,.018,'Six payload patterns. Model-matched rectangular waveforms and white noise; synthetic results do not establish RF sensitivity.',ha='center',fontsize=8)
fig.tight_layout(rect=[0,.06,1,.94]);out=HERE.parents[2]/'images/synthetic-stress.svg';fig.savefig(out);fig.savefig(out.with_suffix('.png'),dpi=160)
