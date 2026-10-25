"""Offline repeat analysis. No UHD, serial, network forwarding or TX APIs.
Replays normal decoder on a four-second burst excerpt, then measures known preamble.
"""
import sys,json,zlib,hashlib,csv
from pathlib import Path
import numpy as np
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive',type=Path,help='Dated bench archive containing both original run directories')
parser.add_argument('decoder',type=Path,help='Directory containing the unchanged normal modem.py')
parser.add_argument('output',type=Path,help='New output directory; never overwritten')
args=parser.parse_args()
sys.path.insert(0,str(args.decoder))
import modem
base=args.archive
out=args.output
out.mkdir(exist_ok=False)
n=np.arange(129)-64
taps=2*(18000/192000)*np.sinc(2*(18000/192000)*n)*np.hamming(129);taps/=taps.sum()
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
report=dict(analysis='Offline only, no forwarding or additional RF transmissions',captures=[])
for run,digest in [('rx-burst-dual-01','4104665e'),('rx-burst-dual-02','74342ca7')]:
 directory=base/run
 item=dict(run=run,expected_native_crc32_hex=digest,channels=[])
 powers=[]
 for channel in (0,1):
  raw=np.load(directory/f'raw-rx-channel-{channel}-192k.npy',mmap_mode='r')
  power=np.mean(abs(raw.reshape(-1,1920))**2,axis=1);powers.append(power)
  peak=int(np.argmax(power));median=float(np.median(power))
  on=np.flatnonzero(power>median*100)
  intervals=[]
  if len(on):
   for group in np.split(on,np.flatnonzero(np.diff(on)>1)+1): intervals.append(dict(start_s=float(group[0]/100),stop_s=float((group[-1]+1)/100)))
  if run.endswith('01'):
   prev=json.loads((directory/'analysis.json').read_text())['channels'][channel]
   start=prev['excerpt_start_sample']
   iq=np.load(directory/f'burst-channel-{channel}-baseband-48k.npy')
  else:
   start=max(0,(peak*1920-2*192000)//1920*1920)
   excerpt=np.array(raw[start:start+4*192000]);np.save(out/f'{run}-ch{channel}-raw-192k.npy',excerpt)
   iq=np.convolve(excerpt,taps,mode='same')[::4].astype(np.complex64)
   np.save(out/f'{run}-ch{channel}-baseband-48k.npy',iq)
  packets=modem.decode(iq,single_window=True)
  for packet in packets:
   native=bytes.fromhex(packet['hex']);packet['native_crc32_hex']=f'{zlib.crc32(native):08x}'
   packet['matches_ihu_length_and_digest']=len(native)==38 and packet['native_crc32_hex']==digest
  ch=dict(channel=channel,median_idle_block_power=median,peak_block_power=float(power[peak]),peak_to_median_db=float(10*np.log10(power[peak]/median)),peak_block_time_s=peak/100,active_intervals_20db_over_median=intervals,excerpt_start_sample=start,decoded_packets=packets)
  if channel==0 and len(packets)==1:
   measurement,coarse,refined,states=phase(iq,packets[0]);ch['phase']=measurement
   with (out/f'{run}-preamble.csv').open('w') as f:
    writer=csv.writer(f);writer.writerow(['preamble_symbol_index','state','coarse_cfo_real','coarse_cfo_imag','refined_cfo_real','refined_cfo_imag'])
    for k,s,a,b in zip(range(4,252),states,coarse,refined):writer.writerow([k,s,a.real,a.imag,b.real,b.imag])
  item['channels'].append(ch)
 with (out/f'{run}-power.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['seconds_from_capture_start','ch0_mean_iq_power','ch1_mean_iq_power'])
  for k in range(len(powers[0])):w.writerow([k/100,powers[0][k],powers[1][k]])
 report['captures'].append(item)
(out/'analysis.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
