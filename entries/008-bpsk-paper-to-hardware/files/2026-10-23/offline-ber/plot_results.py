"""Render publication figures from saved CSV counts. No measurements or RF access."""
from pathlib import Path
import argparse,csv,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
COLORS={'libre01':'#1d4ed8','libre02':'#0891b2','pluto00':'#d97706','pluto20':'#dc2626'}
NAMES={'libre01':'LibreSDR 1','libre02':'LibreSDR 2','pluto00':'Pluto 0 dB','pluto20':'Pluto 20 dB'}
def read(path):return list(csv.DictReader(path.open()))
def selected(rows,curve):return sorted((r for r in rows if r['curve']==curve),key=lambda r:float(r['ebn0_db']))
def points(ax,rows,curve,label,color,marker):
    records=selected(rows,curve)
    for i,r in enumerate(records):
        y=float(r['ber']);x=float(r['ebn0_db'])
        if y==0:continue
        sparse=r['sparse_tail']=='True'
        ax.errorbar([x],[y],yerr=[[max(0,y-float(r['ci95_low']))],[max(0,float(r['ci95_high'])-y)]],fmt=marker,color=color,markersize=5,mfc='none' if sparse else color,capsize=2,label=label if i==0 else None,alpha=.85)
def save(fig,dest,name):
    fig.savefig(dest/(name+'.svg'));fig.savefig(dest/(name+'.png'),dpi=150);plt.close(fig)
def main(data,dest):
    dest.mkdir(parents=True,exist_ok=True);plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
    fast=read(data/'fast-summary.csv');paper=read(data/'paper-summary.csv');cfo=read(data/'cfo-check.csv')
    squared=read(data/'scheduled-summary.csv');template=read(data/'template-summary.csv')
    x=np.linspace(-4,12,321);g=10**(x/10);coh=np.array([.5*math.erfc(math.sqrt(t)) for t in g]);diff=.5*np.exp(-g)
    fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained')
    fig.suptitle('From ideal BPSK to the recorded transceiver waveform',fontsize=15)
    axes[0].semilogy(x,diff,color='#111827',label='Ideal DBPSK theory')
    points(axes[0],fast,'ideal_dbpsk_random_data','Ideal DBPSK random bits','#64748b','x')
    points(axes[0],fast,'ideal135_known55_dbpsk_data','135° rectangular model','#a21caf','D')
    axes[1].semilogy(x,coh,color='#111827',label='Ideal coherent BPSK theory')
    geometry=np.sin(np.deg2rad(135/2))**2
    axes[1].semilogy(x,[.5*math.erfc(math.sqrt(t*geometry)) for t in g],color='#a21caf',label='135° two-state coherent theory')
    points(axes[1],fast,'ideal135_known55_coherent_phase','135° model phase decisions','#a21caf','D')
    for name,marker in zip(COLORS,['o','s','^','v']):
        points(axes[0],fast,name+'_frozen_dbpsk_data',NAMES[name],COLORS[name],marker)
        points(axes[1],fast,name+'_frozen_coherent_phase',NAMES[name],COLORS[name],marker)
    for ax in axes:
        ax.set(xlabel='Normalized replay $E_b/N_0$ (dB)',ylabel='Bit error fraction',xlim=(-4.5,12.5),ylim=(1e-6,1));ax.grid(which='both',alpha=.2);ax.legend(fontsize=8,loc='lower left')
    axes[0].set_title('Original data bits: differential detection')
    axes[1].set_title('Phase-state bits: coherent nearest-center bound')
    fig.supxlabel('Capture CFO/timing frozen from clean reference; 184 held-out known preamble bits × 6000 noise trials per point.\nWhite noise at the 48 ksample/s replay plane. Trial-block 95% intervals; open markers <100 errors; zero-error points omitted.\nRight panel scores phase states, not decoded native data. Neither panel is analog receiver sensitivity.',fontsize=9)
    save(fig,dest,'offline-waveform-ber')

    fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained')
    fig.suptitle('Reproducing the paper model separately from hardware replay',fontsize=15)
    axes[0].semilogy(x,coh,color='#111827',label='Ideal coherent BPSK theory')
    for npre,color,marker in [(16,'#d97706','s'),(64,'#1d4ed8','o')]:points(axes[0],paper,f'paper_pn{npre}_coherent_compensated',f'Known PN preamble {npre}',color,marker)
    nu=.1;ns=8;k=np.arange(64);amp=np.sin(np.pi*nu)/(ns*np.sin(np.pi*nu/ns));phase=2*np.pi*nu*(k+(ns-1)/(2*ns))
    finite=np.array([np.mean([.5*math.erfc(math.sqrt(t)*amp*np.cos(p)) for p in phase]) for t in g])
    axes[0].semilogy(x,finite,color='#64748b',label='Finite 64-bit uncompensated theory')
    points(axes[0],paper,'paper_uncompensated','Uncompensated offset','#64748b','x')
    axes[0].set(title='Preamble frequency + one phase correction',xlabel='$E_b/N_0$ (dB)',ylabel='Data BER',xlim=(-4.5,12.5),ylim=(1e-6,1));axes[0].grid(which='both',alpha=.2);axes[0].legend(fontsize=8,loc='lower left')
    v=np.linspace(0,.5,201);gain=np.ones_like(v);gain[1:]=np.sin(np.pi*v[1:])/(8*np.sin(np.pi*v[1:]/8))
    theory=[.5*math.erfc(math.sqrt(10**.8)*a) for a in gain]
    continuous=[.5*math.erfc(math.sqrt(10**.8)*np.sinc(a)) for a in v]
    axes[1].semilogy(v,theory,color='#111827',label='Exact discrete Ns=8 theory');axes[1].semilogy(v,continuous,color='#64748b',ls='--',label='Continuous sinc approximation')
    axes[1].semilogy([float(r['nu']) for r in cfo],[float(r['ber']) for r in cfo],'o',color='#1d4ed8',label='Monte Carlo, 8 dB')
    axes[1].set(title='Within-symbol CFO loss, symbol-center oracle',xlabel='Residual offset / symbol rate',ylabel='Data BER at 8 dB',xlim=(0,.5),ylim=(1e-4,.03));axes[1].grid(which='both',alpha=.2);axes[1].legend(fontsize=8,loc='upper left')
    fig.supxlabel('Left: paper parameters Ns=8, normalized CFO=0.10, 64 data bits; 18,000 packets / 1,152,000 bits per point.\nIndependent NumPy RNG and fixed budgets; algorithm/equation reproduction, not bit-identical MATLAB output.\nRight: per-symbol phase oracle isolates integration loss; this is not an uncompensated packet receiver.',fontsize=9)
    save(fig,dest,'offline-paper-model')

    fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained')
    fig.suptitle('Synchronization loss and a paper-inspired diagnostic alternative',fontsize=15)
    axes[0].semilogy(x,diff,color='#111827',label='Ideal DBPSK theory')
    points(axes[0],fast,'pluto20_frozen_dbpsk_data','Pluto 20 dB: frozen CFO/timing','#dc2626','s')
    points(axes[0],squared,'pluto20','Squared-IQ CFO + training timing','#d97706','^')
    points(axes[0],template,'pluto20','Learned 64-symbol template CFO','#1d4ed8','o')
    axes[0].set(title='All scheduled preamble decisions retained',xlabel='Normalized replay $E_b/N_0$ (dB)',ylabel='Known preamble BER',xlim=(-4.5,12.5),ylim=(1e-4,1));axes[0].grid(which='both',alpha=.2);axes[0].legend(fontsize=8,loc='lower left')
    for table,color,label in [(squared,'#d97706','Squared-IQ'),(template,'#1d4ed8','Learned template')]:
        values=selected(table,'pluto20');eb=[float(r['ebn0_db']) for r in values]
        prefix='scheduled' if label=='Squared-IQ' else 'template'
        intervals=read(data/'sync-frame-intervals.csv')
        for metric,marker,caption in [('exact_sync','o','exact sync'),('scheduled_sync_plus_crc32','s','sync + body CRC32')]:
            r=sorted([r for r in intervals if r['method']==prefix and r['capture']=='pluto20' and r['observation']==metric],key=lambda r:float(r['ebn0_db']))
            y=np.array([float(v['fraction']) for v in r]);low=np.array([float(v['ci95_low']) for v in r]);high=np.array([float(v['ci95_high']) for v in r])
            axes[1].errorbar(eb,y,yerr=[np.maximum(0,y-low),np.maximum(0,high-y)],fmt=marker,mfc='none' if marker=='s' else color,color=color,capsize=2,label=label+': '+caption)
    axes[1].set(title='Scheduled sync/frame observations, pilot budget',xlabel='Normalized replay $E_b/N_0$ (dB)',ylabel='Fraction of 150 replay trials',xlim=(-4.5,12.5),ylim=(-.02,1.02));axes[1].grid(alpha=.2);axes[1].legend(fontsize=8,loc='upper left')
    fig.supxlabel('Pilot: 3 seeds × 50 trials per point, known scheduled 4-second window, 60-symbol timing metric; CRC never gates BER.\nTemplate method uses prior clean hardware state centers and scheduled preamble timing; not a blind/live receiver replacement.\nBody bits are a clean-decode replay reference; frame fractions are not independent over-the-air packet-success statistics.',fontsize=9)
    save(fig,dest,'offline-synchronization')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('data',type=Path);p.add_argument('destination',type=Path);a=p.parse_args();main(a.data,a.destination)
