"""Reproducible offline paper/capture comparison. Never opens a radio or console.

Run sections into one NEW output directory; section outputs are never overwritten.
Default fixed budgets: fast 3*2000*184=1,104,000 scored bits/point;
paper 3*6000*64=1,152,000 data bits/point; scheduled pilot 3*50 trials/point.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,json,math,platform,time
import numpy as np
import diagnostic as d
HERE=Path(__file__).resolve().parent
GRID=list(range(-4,13,2))
SEEDS=[271828,314159,161803]

def dump(path,value):
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(value,indent=2)+'\n')

def table(path,rows):
    if path.exists():raise FileExistsError(path)
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def row(section,curve,eb,counts,nbits,**extra):
    ber,lo,hi,method=d.cluster_interval(counts,nbits)
    return dict(section=section,curve=curve,ebn0_db=eb,trials=len(counts),scored_bits=len(counts)*nbits,
        bit_errors=int(np.sum(counts)),ber=ber,ci95_low=lo,ci95_high=hi,interval_method=method,
        trials_with_errors=int(np.count_nonzero(counts)),sparse_tail=bool(np.sum(counts)<100),**extra)

def inputs():
    manifest=json.loads((HERE/'manifest.json').read_text());refs={}
    for source in manifest['sources']:
        path=HERE/source['filename']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=source['npz_sha256']:raise ValueError('Input hash mismatch')
        iq=np.load(path,allow_pickle=False)['iq'];r=d.freeze(iq,source)
        if r['known_preamble_baseline']['bit_errors'] or not r['original_frame_crc_pass']:raise ValueError('Clean calibration failed')
        refs[source['name']]=r
    return manifest,refs

def prepare(out,refs):
    public={};symbols=[]
    for name,r in refs.items():
        public[name]={k:v for k,v in r.items() if k not in ('symbols','normalized_iq','expected_bits','expected_states')}
        for k,z in enumerate(r['symbols']):symbols.append(dict(capture=name,symbol_index=k,clean_mf_real=z.real,clean_mf_imag=z.imag,expected_bit=int(r['expected_bits'][k]),expected_phase_state=int(r['expected_states'][k]),independently_known_preamble=k<256,training=k in d.TRAIN,scored_known_preamble=k in d.SCORE))
    dump(out/'frozen-references.json',public);table(out/'clean-symbols.csv',symbols)
    dump(out/'config.json',dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),python=platform.python_version(),numpy=np.__version__,grid_db=GRID,seeds=SEEDS,noise_trials_per_seed=args.noise_trials,paper_packets_per_seed=args.paper_packets,pilot_trials_per_seed=args.pilot_trials,score_bits_per_capture_trial=len(d.SCORE),score_indices=d.SCORE.tolist(),training_indices=d.TRAIN.tolist(),expected_capture_names=list(refs),truth='Score independently known 0x55 preamble; replay body disagreements are separately labelled.',noise_plane='White circular complex noise added at the already recorded 48k replay plane before rectangular integration. Recorded analog/FPGA/decimation filters are part of the fixed waveform. This does not simulate noise before the original physical filters or analog sensitivity.',normalization='Mean observed preamble sample energy minus idle sample power, times 40, is normalized to 1. Added noise N0=10^(-EbN0/10) minus estimated existing matched-filter complex noise variance; existing waveform/noise retained. Sufficient-statistic injection in fast section is exact for new white noise with frozen CFO/timing.',intervals='Independent injected-noise trial blocks conditional on each one fixed waveform. Normal cluster intervals for nonzero errors, sparse counts flagged. Zero-error upper bound uses independent trials, not differential bit independence.',paper='Ns=8, Nb=64, nu=0.10, phi=0, known PN Np=16/64, ML FFT with 16x zero-padding and parabolic interpolation, one preamble phase correction; independent NumPy RNG differs from MATLAB RNG.'))

def fast(out,refs):
    if (out/'fast-summary.csv').exists():raise FileExistsError('Fast results exist')
    totals={};seedrows=[];raw_errors={}
    known=next(iter(refs.values()))['expected_bits'][:256];states=next(iter(refs.values()))['expected_states'][:256]
    theta=135*np.pi/180
    for eb in GRID:
        n0=10**(-eb/10);counts={}
        for seed in SEEDS:
            rng=np.random.default_rng(np.random.SeedSequence([seed,eb+4,1]))
            n=args.noise_trials
            w=(rng.standard_normal((n,257))+1j*rng.standard_normal((n,257)))/math.sqrt(2)
            bits=rng.integers(0,2,(n,256));random_states=np.c_[np.zeros(n,dtype=int),np.cumsum(bits,axis=1)%2]
            def keep(curve,error):
                e=np.asarray(error)[:,d.SCORE];c=e.sum(axis=1).astype(np.int16)
                counts.setdefault(curve,[]).append(c);seedrows.append(row('fast',curve,eb,c,len(d.SCORE),seed=seed))
                raw_errors[f'{curve}_e{eb}_s{seed}']=np.packbits(e,axis=1)
            coherent=(2*bits-1)+math.sqrt(n0)*w[:,1:]
            keep('ideal_coherent_random_phase',(coherent.real>0)!=bits)
            random_z=(1-2*random_states)+math.sqrt(n0)*w
            keep('ideal_dbpsk_random_data',(np.real(random_z[:,1:]*np.conj(random_z[:,:-1]))<0)!=bits)
            for label,angle in [('ideal180_known55',np.pi),('ideal135_known55',theta)]:
                centers=np.exp(1j*angle*np.arange(2));z=centers[states][None,:]+math.sqrt(n0)*w[:,1:]
                coh,diff=d.decisions(z,centers)
                keep(label+'_dbpsk_data',diff!=known)
                if angle==theta:keep(label+'_coherent_phase',coh!=states)
            for name,r in refs.items():
                added=n0-r['existing_matched_filter_noise_variance']
                if added<=0:raise ValueError('Requested target cleaner than original recording')
                z=r['symbols'][None,:256]+math.sqrt(added)*w[:,1:]
                centers=np.array([complex(*c) for c in r['centers']]);coh,diff=d.decisions(z,centers)
                keep(name+'_frozen_dbpsk_data',diff!=r['expected_bits'][:256])
                keep(name+'_frozen_coherent_phase',coh!=r['expected_states'][:256])
        for curve,v in counts.items():
            c=np.concatenate(v);totals[(curve,eb)]=row('fast',curve,eb,c,len(d.SCORE))
        print('fast',eb,'dB complete',flush=True)
    table(out/'fast-summary.csv',list(totals.values()));table(out/'fast-seeds.csv',seedrows)
    np.savez_compressed(out/'fast-error-masks.npz',**raw_errors)

def paper_frequency_batch(samples,known_wave):
    """Vectorized paper ML FFT/parabolic estimator; cycles per sample."""
    batch,length=samples.shape;nfft=1<<(length*16-1).bit_length()
    spec=abs(np.fft.fft(samples*np.conj(known_wave),nfft,axis=1));peak=spec.argmax(axis=1);ii=np.arange(batch)
    left=spec[ii,(peak-1)%nfft];mid=spec[ii,peak];right=spec[ii,(peak+1)%nfft]
    denom=left-2*mid+right;delta=np.divide(.5*(left-right),denom,out=np.zeros(batch),where=denom!=0)
    f=(peak+delta)/nfft
    return np.where(f>=.5,f-1,f)

def paper(out):
    if (out/'paper-summary.csv').exists():raise FileExistsError('Paper results exist')
    rows=[];seedrows=[];all_counts={}
    ns=8;nb=64;nu=.10;phi=0.
    for eb in GRID:
        n0=10**(-eb/10)
        for npre in (16,64):
            name=f'paper_pn{npre}_coherent_compensated'
            pn=np.random.default_rng(12345).integers(0,2,npre);a_pre=2*pn-1
            pw=np.repeat(a_pre,ns)/math.sqrt(ns);length=(npre+nb)*ns
            nfft=1<<(npre*ns*16-1).bit_length();counts=[]
            for seed in SEEDS:
                rng=np.random.default_rng(np.random.SeedSequence([seed,eb+4,npre,2]));c=[]
                for k in range(0,args.paper_packets,100):
                    batch=min(100,args.paper_packets-k)
                    data=rng.integers(0,2,(batch,nb));bits=np.c_[np.tile(pn,(batch,1)),data]
                    wave=np.repeat(2*bits-1,ns,axis=1)/math.sqrt(ns)
                    x=wave*np.exp(1j*(2*np.pi*nu*np.arange(length)/ns+phi))[None,:]
                    x=x+math.sqrt(n0/2)*(rng.standard_normal(x.shape)+1j*rng.standard_normal(x.shape))
                    f=paper_frequency_batch(x[:,:npre*ns],pw)
                    fixed=x*np.exp(-2j*np.pi*f[:,None]*np.arange(length)[None,:])
                    z=fixed.reshape(batch,npre+nb,ns).sum(axis=2)/math.sqrt(ns)
                    phase=np.angle(np.sum(z[:,:npre]*a_pre,axis=1))
                    detected=(np.real(z[:,npre:]*np.exp(-1j*phase[:,None]))>0)
                    c.extend(np.sum(detected!=data,axis=1).tolist())
                c=np.asarray(c,dtype=np.int16);counts.append(c);seedrows.append(row('paper',name,eb,c,nb,seed=seed));all_counts[f'{name}_e{eb}_s{seed}']=c
            c=np.concatenate(counts);rows.append(row('paper',name,eb,c,nb,packet_failures=int(np.count_nonzero(c)),packet_success=float(np.mean(c==0))))
        # Uncompensated nu=.1, matched filter Ns=8, starting phase zero.
        counts=[]
        for seed in SEEDS:
            rng=np.random.default_rng(np.random.SeedSequence([seed,eb+4,0,2]));n=args.paper_packets
            data=rng.integers(0,2,(n,nb));positions=np.arange(nb)*ns+(ns-1)/2
            attenuation=np.sin(np.pi*nu)/(ns*np.sin(np.pi*nu/ns))
            clean=(2*data-1)*attenuation*np.exp(2j*np.pi*nu*positions/ns)
            noisy=clean+math.sqrt(n0/2)*(rng.standard_normal(clean.shape)+1j*rng.standard_normal(clean.shape))
            c=((noisy.real>0)!=data).sum(axis=1);counts.append(c);seedrows.append(row('paper','paper_uncompensated',eb,c,nb,seed=seed))
        c=np.concatenate(counts);rows.append(row('paper','paper_uncompensated',eb,c,nb))
        print('paper',eb,'dB complete',flush=True)
    table(out/'paper-summary.csv',rows);table(out/'paper-seeds.csv',seedrows);np.savez_compressed(out/'paper-error-counts.npz',**all_counts)

def practical(out,refs,method="square"):
    prefix="scheduled" if method=="square" else "template"
    if (out/(prefix+'-summary.csv')).exists():raise FileExistsError('Pilot results exist')
    rows=[];seedrows=[];ledger=gzip.open(out/(prefix+'-diagnostic-trials.jsonl.gz'),'xt')
    for name in ('libre02','pluto20'):
        ref=refs[name]
        for eb in GRID:
            n0=10**(-eb/10);added=n0-ref['existing_matched_filter_noise_variance'];counts=[];sync=[];crcs=[];frames=[];body=[];cfos=[];conditional=[];erased=0
            for seed in SEEDS:
                rng=np.random.default_rng(np.random.SeedSequence([seed,eb+4,3]));seedcounts=[]
                for trial in range(args.pilot_trials):
                    w=math.sqrt(added/2)*(rng.standard_normal(len(ref['normalized_iq']))+1j*rng.standard_normal(len(ref['normalized_iq'])))
                    result=d.scheduled_diagnostic(ref['normalized_iq']+w,ref,method)
                    if not result['scorable']:
                        erased+=1;ledger.write(json.dumps(dict(capture=name,ebn0_db=eb,seed=seed,trial=trial,**result))+'\n');continue
                    e=result['bit_errors'];counts.append(e);seedcounts.append(e);sync.append(result['sync_exact']);crcs.append(result['outer_crc32_pass']);frames.append(result['scheduled_frame_pass']);body.append(result['replay_reference_body_errors']);cfos.append(result['carrier_estimate_hz']-ref['cfo_hz'])
                    if result['sync_exact']:conditional.append(e)
                    bits=result.pop('bits');result['decisions_hex']=np.packbits(np.maximum(bits,0).astype(np.uint8)).tobytes().hex();result['unobserved_bit_indices']=[0]
                    ledger.write(json.dumps(dict(capture=name,ebn0_db=eb,seed=seed,trial=trial,**result))+'\n')
                if seedcounts:seedrows.append(row(prefix,name,eb,seedcounts,len(d.SCORE),seed=seed))
            rows.append(row(prefix,name,eb,counts,len(d.SCORE),scheduled_trials=args.pilot_trials*len(SEEDS),erased_trials=erased,sync_exact_count=int(np.sum(sync)),sync_exact_fraction=float(np.mean(sync)),outer_crc32_count=int(np.sum(crcs)),outer_crc32_fraction=float(np.mean(crcs)),scheduled_frame_pass_count=int(np.sum(frames)),scheduled_frame_pass_fraction=float(np.mean(frames)),sync_conditioned_scored_bits=len(conditional)*len(d.SCORE),sync_conditioned_errors=int(np.sum(conditional)),sync_conditioned_ber=float(np.sum(conditional)/(len(conditional)*len(d.SCORE))) if conditional else None,replay_reference_body_scored_bits=len(body)*392,replay_reference_body_errors=int(np.sum(body)),carrier_error_rmse_hz=float(np.sqrt(np.mean(np.asarray(cfos)**2)))))
            print(prefix,name,eb,'dB complete',flush=True)
    ledger.close();table(out/(prefix+'-summary.csv'),rows);table(out/(prefix+'-seeds.csv'),seedrows)

def cfo_check(out):
    rows=[];ns=8;eb=8;g=10**(eb/10);n0=1/g
    for nu in (0.,.1,.25,.5):
        amp=1. if nu==0 else np.sin(np.pi*nu)/(ns*np.sin(np.pi*nu/ns))
        # Independently integrate the rotating Ns=8 pulse; formula is theory only.
        mc_amplitude=float(np.mean(np.exp(2j*np.pi*nu*(np.arange(ns)-(ns-1)/2)/ns)).real)
        counts=[]
        for seed in SEEDS:
            rng=np.random.default_rng(np.random.SeedSequence([seed,int(nu*100),4]));bits=rng.integers(0,2,(2000,184))
            stat=(2*bits-1)*mc_amplitude+math.sqrt(n0/2)*rng.standard_normal(bits.shape)
            counts.extend(np.sum((stat>0)!=bits,axis=1).tolist())
        rows.append(row('cfo','paper_symbol_center_oracle',eb,counts,184,nu=nu,discrete_loss_db=20*math.log10(abs(amp)),theory_discrete=.5*math.erfc(math.sqrt(g)*abs(amp)),theory_continuous=.5*math.erfc(math.sqrt(g)*np.sinc(nu))))
    table(out/'cfo-check.csv',rows)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--section',choices=['prepare','fast','paper','scheduled','template','cfo','all'],default='all');p.add_argument('--noise-trials',type=int,default=2000);p.add_argument('--paper-packets',type=int,default=6000);p.add_argument('--pilot-trials',type=int,default=50);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    _,refs=inputs()
    if args.section in ('prepare','all'):prepare(args.output,refs)
    if args.section in ('fast','all'):fast(args.output,refs)
    if args.section in ('paper','all'):paper(args.output)
    if args.section in ('scheduled','all'):practical(args.output,refs)
    if args.section in ('template','all'):practical(args.output,refs,'template')
    if args.section in ('cfo','all'):cfo_check(args.output)
