"""Scientific comparison rendered from audited counts only."""
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
H=Path(__file__).resolve().parent;rows=list(csv.DictReader((H/'stress-summary.csv').open()))
fig,axes=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
methods=['sequence','preamble_only','tracked'];labels=['Frozen v4','Preamble correction','Tracking α=.06'];colors=['#616f80','#de9932','#147f92']
profiles=['static','residual010','ramp100','walk12'];x=np.arange(len(profiles));w=.24
for j,(m,label,c) in enumerate(zip(methods,labels,colors)):
 values=[next(float(r['conditional_payload_ber'])*100 for r in rows if r['stage']=='detector' and r['profile']==p and r['ebn0_db']=='8' and r['method']==m) for p in profiles]
 axes[0].bar(x+(j-1)*w,values,w,label=label,color=c)
axes[0].set(xticks=x,xticklabels=['Static','120 Hz','100 Hz/s','12° walk'],ylabel='Known payload BER (%)',title='True timing supplied • 8 dB');axes[0].set_ylim(0,6)
profiles=['static','ramp5','ramp100','walk3','walk12'];x=np.arange(len(profiles))
for j,(m,label,c) in enumerate(zip(methods,labels,colors)):
 values=[next(int(r['packets']) for r in rows if r['stage']=='full' and r['profile']==p and r['ebn0_db']=='8' and r['method']==m) for p in profiles]
 axes[1].bar(x+(j-1)*w,values,w,label=label,color=c)
axes[1].set(xticks=x,xticklabels=['Static','5 Hz/s','100 Hz/s','3° walk','12° walk'],ylabel='Exact packets / 54 trials',title='Unknown timing and CFO • 8 dB');axes[1].set_ylim(0,56);axes[1].tick_params(axis='x',rotation=25)
cap=list(csv.DictReader((H/'capture-comparison.csv').open()));x=np.arange(3)
for j,(m,label,c) in enumerate([('old','Frozen v4',colors[0]),('new','New receiver',colors[2])]):
 axes[2].bar(x+(j-.5)*.32,[int(r[m+'_packets']) for r in cap],.32,label=label,color=c)
axes[2].set(xticks=x,xticklabels=['Clean (3)','8 dB (90)','12 dB (90)'],ylabel='CRC-passing packets',title='Retrospective saved RF captures');axes[2].set_ylim(0,95)
for ax in axes:ax.spines[['top','right']].set_visible(False);ax.set_axisbelow(True);ax.grid(axis='y',alpha=.2)
fig.legend(labels,loc='outside lower center',ncol=3,frameon=False)
fig.suptitle('Tracking fixes residual CFO; the loop also introduces regressions',fontsize=14)
fig.savefig(H/'comparison.svg');fig.savefig(H/'comparison.png',dpi=140)
