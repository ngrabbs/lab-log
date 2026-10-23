"""Offline Pluto decode and known-preamble phase comparison. No device access or TX."""
import sys,json,zlib,hashlib,csv
from pathlib import Path
import numpy as np
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive',type=Path,help='Dated archive containing pluto-burst-01/')
parser.add_argument('decoder',type=Path,help='Directory with unchanged normal modem.py')
parser.add_argument('output',type=Path,help='New analysis directory; never overwritten')
args=parser.parse_args()
sys.path.insert(0,str(args.decoder))
import modem
base=args.archive
out=args.output
out.mkdir(exist_ok=False)
def stats(points,states):
 centers=np.array([points[states==s].mean() for s in (0,1)])
 return dict(separation_deg=float(abs(np.angle(centers[1]*centers[0].conjugate()))*180/np.pi),amplitude_ratio=float(abs(centers[1])/abs(centers[0])),phase_std_deg=[float(np.std(np.angle(points[states==s]*centers[s].conjugate()))*180/np.pi) for s in (0,1)],metric=float(np.mean(abs(points-centers[states])**2)/np.mean(abs(points)**2)))
def phase(iq,packet):
 corrected=iq*np.exp(-2j*np.pi*packet['carrier_offset_hz']*np.arange(len(iq))/48000)
 integ=np.r_[0,np.cumsum(corrected)]
 known=np.unpackbits(np.frombuffer(modem.frame(bytes.fromhex(packet['hex']),packet['sequence']),np.uint8))
 states=(np.cumsum(known[:256])%2).astype(int)[4:252]
 candidates=[]
 sync=np.unpackbits(np.frombuffer(modem.SYNC,np.uint8))
 for timing in range(40):
  bounds=np.arange(timing,len(iq)+1,40)
  symbols=np.diff(integ[bounds]);bits=(np.real(symbols[1:]*np.conj(symbols[:-1]))<0).astype(np.uint8)
  hits=np.flatnonzero(np.all(np.lib.stride_tricks.sliding_window_view(bits,32)==sync,axis=1))
  for hit in hits:
   if hit<255: continue
   recovered=modem.recover_bits(bits[hit:])
   if not any(p['hex']==packet['hex'] and p['sequence']==packet['sequence'] for p in recovered):continue
   start=int(hit)-255
   points=np.array([corrected[timing+(start+k)*40+16:timing+(start+k)*40+24].mean() for k in range(4,252)])
   metric=stats(points,states)
   candidates.append(dict(timing_sample=timing,preamble_start_symbol_index=start,**metric,points=points))
 if not candidates: raise RuntimeError('No CRC-valid preamble alignment')
 best=min(candidates,key=lambda c:c['metric']);points=best.pop('points')
 centers=np.array([points[states==s].mean() for s in (0,1)])
 times=np.arange(4,252)/1200
 slope,_=np.polyfit(times,np.unwrap(np.angle(points*np.conj(centers[states]))),1)
 refined=points*np.exp(-1j*slope*times)
 residual=float(slope/(2*np.pi))
 public_candidates=[]
 for c in candidates:
  v=c.get('points',points);mu=np.array([v[states==s].mean() for s in (0,1)])
  m,_=np.polyfit(times,np.unwrap(np.angle(v*np.conj(mu[states]))),1)
  public_candidates.append(dict({k:v for k,v in c.items() if k!='points'},after_common_refinement=stats(v*np.exp(-1j*m*times),states),residual_cfo_hz=float(m/(2*np.pi))))
 return dict(method='Same known-preamble method as capture 01: 129-tap lowpass and 4:1 decimation; normal squared-IQ CFO; search 40 symbol timings among CRC-valid alignments, minimize normalized within-state complex variance on central 8/40 samples of 248 preamble symbols; omit four symbols at each end. One additional common linear phase slope, independent state centers; no per-symbol rotation.',best=best,candidates=public_candidates,refinement=dict(residual_cfo_hz=residual,refined_relative_cfo_hz=float(packet['carrier_offset_hz']+residual),**stats(refined,states))),points,refined,states

directory=base/'pluto-burst-01'
source=directory/'raw-iq-int16.npy'
capture=json.loads((directory/'result.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==capture['raw_file']['sha256']
raw=np.load(source,mmap_mode='r')
# Compute digital mean IQ power over 10 ms blocks, normalizing 12-bit samples.
blocks=raw.reshape(-1,2880,2).astype(np.float64)/2048
power=np.mean(np.sum(blocks**2,axis=2),axis=1);del blocks
peak=int(np.argmax(power));median=float(np.median(power))
active=np.flatnonzero(power>float(power[peak])*.01)
intervals=[]
if len(active):
 for group in np.split(active,np.flatnonzero(np.diff(active)>1)+1):intervals.append(dict(start_s=float(group[0]/100),stop_s=float((group[-1]+1)/100)))
start=max(0,(peak*2880-2*288000)//2880*2880)
excerpt=raw[start:start+4*288000].astype(np.float64)/2048
iqraw=(excerpt[:,0]+1j*excerpt[:,1]).astype(np.complex64)
np.save(out/'burst-raw-288k.npy',iqraw)
report=dict(raw_hash_verified=True,iq_rate_hz=288000,excerpt_start_sample=start,peak_block_time_s=peak/100,peak_block_power=float(power[peak]),median_idle_block_power=median,peak_to_median_db=float(10*np.log10(power[peak]/median)) if median>0 else None,active_intervals_20db_below_peak=intervals,burst_threshold_note='Peak-relative threshold only; median idle block power is zero at this gain/quantization. No idle-referenced SNR inferred.',zero_power_block_fraction=float(np.count_nonzero(power==0)/len(power)),nonzero_sample_fraction=float(np.count_nonzero(np.any(raw!=0,axis=1))/len(raw)),filters=[],expected_native_bytes=38,expected_native_crc32_hex='13049149',forwarded=False)
for ntaps in (193,129):
 n=np.arange(ntaps)-(ntaps-1)//2
 taps=2*(18000/288000)*np.sinc(2*(18000/288000)*n)*np.hamming(ntaps);taps/=taps.sum()
 iq=np.convolve(iqraw,taps,mode='same')[::6].astype(np.complex64)
 np.save(out/f'baseband-48k-{ntaps}tap.npy',iq)
 packets=modem.decode(iq,single_window=True)
 item=dict(filter_taps=ntaps,filter_cutoff_hz=18000,decimation=6,decoded_packets=packets)
 for packet in packets:
  native=bytes.fromhex(packet['hex']);packet['native_crc32_hex']=f'{zlib.crc32(native):08x}'
  packet['matches_ihu_length_and_digest']=len(native)==38 and packet['native_crc32_hex']=='13049149'
 if len(packets)==1:
  measurement,coarse,refined,states=phase(iq,packets[0]);measurement['method']=measurement['method'].replace('129-tap lowpass and 4:1 decimation',f'{ntaps}-tap 18 kHz lowpass and 6:1 decimation from Pluto 288 ksample/s; all subsequent steps identical')
  item['phase']=measurement
  with (out/f'preamble-{ntaps}tap.csv').open('w') as f:
   w=csv.writer(f);w.writerow(['preamble_symbol_index','state','coarse_cfo_real','coarse_cfo_imag','refined_cfo_real','refined_cfo_imag'])
   for k,s,a,b in zip(range(4,252),states,coarse,refined):w.writerow([k,s,a.real,a.imag,b.real,b.imag])
 report['filters'].append(item)
with (out/'power.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['seconds_from_capture_start','mean_iq_power'])
 for k in range(len(power)):w.writerow([k/100,power[k]])
(out/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
