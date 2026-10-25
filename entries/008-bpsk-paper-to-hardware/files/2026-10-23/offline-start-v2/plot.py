"""Static count figure calculated from the saved paired summary."""
from pathlib import Path
import csv,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
rows={int(r['ebn0_db']):r for r in csv.DictReader((HERE/'paired-summary.csv').open()) if r['capture']=='ALL' and r['ebn0_db']!='ALL'}
def interval(k,n):
 z=1.95996398454;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return max(0,c-h)*n,min(1,c+h)*n
plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
fig,axes=plt.subplots(1,2,figsize=(9.2,4.1),sharey=True)
for ax,outcome,title in zip(axes,['start','frame'],['Correct frame start','Exact sync + outer CRC32']):
 for j,version,color in [(0,'v1','#747d8c'),(1,'v2','#087f8c')]:
  x=[i+(j-.5)*.34 for i in range(2)];counts=[int(rows[eb][outcome+'_'+version+'_pass']) for eb in [8,12]]
  cis=[interval(k,90) for k in counts]
  ax.bar(x,counts,width=.31,color=color,label=version.upper())
  ax.errorbar(x,counts,yerr=[[max(0,k-ci[0]) for k,ci in zip(counts,cis)],[max(0,ci[1]-k) for k,ci in zip(counts,cis)]],fmt='none',ecolor='#222',capsize=3,lw=1)
  for xx,k in zip(x,counts):ax.text(xx,max(7,k*.48),str(k),ha='center',color='white' if k>10 else '#222',fontweight='bold')
 ax.set_xticks([0,1],['8 dB','12 dB']);ax.set_title(title);ax.set_xlabel('Normalized replay Eb/N0');ax.set_ylim(0,97);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
axes[0].set_ylabel('Successful trials / 90');axes[0].legend(loc='upper left')
fig.suptitle('Frozen training-only revision, paired reused held-out recordings',fontsize=12)
fig.text(.5,.015,'Bars: saved trial counts. Whiskers: 95% Wilson intervals over injected-noise trials; fixed RF recordings.',ha='center',fontsize=8)
fig.tight_layout(rect=[0,.06,1,.95])
image=HERE.parents[2]/'images/frame-start-v2.svg';fig.savefig(image)
fig.savefig(image.with_suffix('.png'),dpi=160)
