"""Plot audited results, without receiver/model selection."""
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;rows=list(csv.DictReader((H/'stress-summary.csv').open()))
fig,axes=plt.subplots(1,3,figsize=(14,4.6),layout='constrained')
methods=['sequence','preamble_only','continuous','gated'];labels=['Frozen v4','Preamble only','Continuous .06','Confidence gate'];colors=['#657184','#e2a138','#87b5c1','#087b80'];w=.19
profiles=['static','residual010','ramp100','walk12'];x=np.arange(len(profiles))
for j,(method,label,color) in enumerate(zip(methods,labels,colors)):
 values=[next(float(r['conditional_payload_ber'])*100 for r in rows if r['stage']=='detector' and r['profile']==p and r['ebn0_db']=='8' and r['method']==method) for p in profiles]
 axes[0].bar(x+(j-1.5)*w,values,w,color=color,label=label)
axes[0].set(xticks=x,xticklabels=['Static','120 Hz','100 Hz/s','12° walk'],ylabel='Known payload BER (%)',title='Known timing • 8 dB',ylim=(0,6))
profiles=['static','ramp5','ramp100','walk3','walk12'];x=np.arange(len(profiles))
for j,(method,color) in enumerate(zip(methods,colors)):
 values=[next(int(r['packets']) for r in rows if r['stage']=='full' and r['profile']==p and r['ebn0_db']=='8' and r['method']==method) for p in profiles]
 axes[1].bar(x+(j-1.5)*w,values,w,color=color)
axes[1].set(xticks=x,xticklabels=['Static','5 Hz/s','100 Hz/s','3° walk','12° walk'],ylabel='Exact packets / 54',title='Unknown timing and CFO • 8 dB',ylim=(0,56));axes[1].tick_params(axis='x',rotation=25)
cap=[r for r in csv.DictReader((H/'capture-by-source.csv').open()) if r['ebn0_db']=='8'];x=np.arange(3)
for j,(field,color) in enumerate(zip(['v4_packets','preamble_only_packets','continuous_packets','gated_packets'],colors)):
 axes[2].bar(x+(j-1.5)*w,[int(r[field]) for r in cap],w,color=color)
axes[2].set(xticks=x,xticklabels=[r['capture'] for r in cap],ylabel='CRC-passing replay packets / 30',title='Saved RF at 8 dB • regressions remain',ylim=(0,31))
for ax in axes:ax.spines[['top','right']].set_visible(False);ax.set_axisbelow(True);ax.grid(axis='y',alpha=.2)
fig.legend(labels,loc='outside lower center',ncol=4,frameon=False)
fig.suptitle('Confidence gating preserves synthetic drift gains; RF limitation remains',fontsize=14)
fig.savefig(H/'comparison.svg');fig.savefig(H/'comparison.png',dpi=140)
