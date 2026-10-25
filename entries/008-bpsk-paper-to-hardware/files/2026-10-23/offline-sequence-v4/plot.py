"""Count-derived 8 dB detector comparison; no simulated or fitted curve."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
paired=[r for r in csv.DictReader((HERE/'paired-summary.csv').open()) if r['ebn0_db']=='8' and r['capture']!='ALL']
classes=[r for r in csv.DictReader((HERE/'bit-class-summary.csv').open()) if r['ebn0_db']=='8' and r['capture']=='ALL']
plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
fig,axes=plt.subplots(1,2,figsize=(10,4.3))
for ax,records,labels,title in [(axes[0],paired,['Libre02','Pluto 0 dB','Pluto 20 dB'],'Held-out capture'),(axes[1],classes,['Unchanged (0)','Changed (1)'],'Bit class, all held-out captures')]:
 for j,v,color in [(0,'v3','#747d8c'),(1,'v4','#087f8c')]:
  xx=[i+(j-.5)*.35 for i in range(len(records))];ys=[100*float(r[v+'_ber']) for r in records]
  ax.bar(xx,ys,width=.32,label=v.upper(),color=color)
  for x,y,r in zip(xx,ys,records):ax.text(x,y+.045,str(r[v+'_errors']),ha='center',fontsize=9)
 ax.set_xticks(range(len(labels)),labels);ax.set_title(title);ax.set_ylim(0,max(float(r[v+'_ber'])*100 for r in records for v in ['v3','v4'])*1.25)
 ax.set_ylabel('Known-preamble BER (%)');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
axes[0].legend()
fig.suptitle('Sequence detector at 8 dB normalized replay Eb/N0',fontsize=12)
fig.text(.5,.025,'Numbers above bars: observed errors. Identical acquired samples; reused RF recordings and post-filter injected noise.',ha='center',fontsize=8)
fig.tight_layout(rect=[0,.07,1,.94])
out=HERE.parents[2]/'images/sequence-v4.svg';fig.savefig(out);fig.savefig(out.with_suffix('.png'),dpi=160)
