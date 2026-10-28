#!/usr/bin/env python3
"""Reproduce summary tables and plots from the immutable decoder JSON outputs."""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows=[]
for run, txname in [('01','tx'),('02','tx02')]:
    rx=json.loads((HERE/f'rx{run}.json').read_text())
    tx=json.loads((HERE/f'{txname}.json').read_text())
    log=(HERE/f'tx{run}.log').read_text().splitlines()
    on=float(next(x.split()[-1] for x in log if x.startswith('PTT ON')))
    off=float(next(x.split()[-1] for x in log if x.startswith('PTT OFF')))
    body_windows=[(p['sync_time_s']+.32,p['sync_time_s']+.32+4)
                  for p in rx['packets']]
    active=[b for b in rx['seconds']
            if any(lo < b['second']+.5 < hi for lo,hi in body_windows)]
    # Last full second is after PTT release in both captures. Median of
    # per-second linear powers in known payload windows gives a robust contrast.
    noise_db=rx['seconds'][23]['channel_power_dbfs']
    total=statistics.median(10**(b['channel_power_dbfs']/10) for b in active)
    noise=10**(noise_db/10)
    contrast=10*math.log10(total/noise)
    expected={p['sequence']:p for p in tx['packets']}
    recovered=sum(p['payload_bytes'] for p in rx['packets'])
    mismatches=sum(sum(a!=b for a,b in zip(p['payload'].encode(),
                      expected[p['sequence']]['payload'].encode()))+
                   abs(len(p['payload'].encode())-expected[p['sequence']]['payload_bytes'])
                   for p in rx['packets'])
    rows.append(dict(run=run,digital_peak=tx['digital_peak'],
                     drive_dbfs_peak=20*math.log10(tx['digital_peak']),
                     packets_sent=len(tx['packets']),packets_crc_ok=len(rx['packets']),
                     payload_bytes_recovered=recovered,payload_byte_mismatches=mismatches,
                     sync_bit_errors=sum(p['sync_bit_errors'] for p in rx['packets']),
                     ptt_s=off-on,payload_bps_including_repeated_messages=recovered*8/(off-on),
                     channel_on_dbfs=10*math.log10(total),channel_off_dbfs=noise_db,
                     channel_on_off_contrast_db=contrast,
                     estimated_signal_to_off_noise_db=10*math.log10((total-noise)/noise),
                     combined_tx_rx_frequency_offset_hz=statistics.median(b['fm_mean_hz'] for b in active),
                     discriminator_frequency_rms_hz=statistics.median(b['fm_rms_hz'] for b in active),
                     adc_rail_fraction=rx['adc_rail_fraction'],
                     payload_window_seconds=[b['second'] for b in active]))
(HERE/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
with (HERE/'summary.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
print(json.dumps(rows,indent=2))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True,layout='constrained')
for run,label in [('01','Run 1: peak 0.10'),('02','Run 2: peak 0.03')]:
    r=json.loads((HERE/f'rx{run}.json').read_text())
    axes[0].plot([b['second']+.5 for b in r['seconds']],
                 [b['channel_power_dbfs'] for b in r['seconds']],'.-',label=label)
    axes[1].plot([b['second']+.5 for b in r['seconds']],
                 [b['fm_rms_hz']/1000 for b in r['seconds']],'.-',label=label)
axes[0].set(ylabel='Channel power (dBFS)',title='446 MHz BPSK audio over FM: two captured bursts\n20 kHz RF channel; fixed RTL tuner gain 0.9 dB')
axes[1].set(ylabel='FM discriminator RMS (kHz)',xlabel='Seconds from each capture start',
            title='Idle FM discriminator noise is high; use the carrier-on intervals for comparison')
for ax in axes:
    ax.grid(alpha=.25);ax.legend(loc='best')
dest=HERE.parent/'images';dest.mkdir(exist_ok=True)
fig.savefig(dest/'capture-comparison.png',dpi=160)
plt.close(fig)

# Hash original IQ, derived audio, manifests and machine-readable results.
names=['rx01.iq','rx02.iq','rx01.wav','rx02.wav','rx01.json','rx02.json',
       'tx.json','tx02.json','tx01.log','tx02.log','rx01-rtl.log','rx02-rtl.log']
with (HERE/'SHA256SUMS').open('w') as out:
    for name in names:
        out.write(hashlib.sha256((HERE/name).read_bytes()).hexdigest()+'  '+name+'\n')
