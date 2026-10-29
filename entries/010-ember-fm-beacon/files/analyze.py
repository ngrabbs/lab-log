#!/usr/bin/env python3
"""Replay saved native packets and recover received CW ID from proof IQ."""
import hashlib
import json
from pathlib import Path
import wave

import numpy as np
from scipy import signal
import radio

HERE=Path(__file__).resolve().parent
MORSE={'-.-':'K','..':'I','.....':'5','-.--':'Y','-.':'N','--.':'G'}
rows=[]
plots=[]
for folder in sorted((HERE/'evidence').glob('20*')):
    original=json.loads((folder/'result.json').read_text())
    replay=radio.receive(folder/'rx.iq')
    assert [(p['sequence'],p['hex']) for p in replay['packets']]==[(p['sequence'],p['hex']) for p in original['packets']]
    raw=np.fromfile(folder/'rx.iq',dtype=np.uint8)
    x=(raw[::2].astype(float)-127.5+1j*(raw[1::2].astype(float)-127.5))/127.5
    x*=np.exp(2j*np.pi*50000*np.arange(len(x))/240000)
    channel=signal.sosfilt(signal.butter(6,10000,fs=240000,output='sos'),x)
    bb=signal.resample_poly(channel,1,5)
    fm=np.angle(bb[1:]*bb[:-1].conj())*48000/(2*np.pi)
    envelope=abs(signal.sosfiltfilt(signal.butter(3,35,fs=48000,output='sos'),
        fm*np.exp(-2j*np.pi*800*np.arange(len(fm))/48000)))
    power=np.mean(abs(channel[:len(channel)//2400*2400].reshape(-1,2400))**2,axis=1)
    gate=np.repeat(power>np.mean(abs(channel[-240000:])**2)*10,480)[:len(envelope)]
    # Acquisition is specific to these captures: packet first, then 20 WPM ID.
    # Exclude startup discriminator artifacts and the packet from CW threshold.
    threshold=np.percentile(envelope[int(1.1*48000):int(4.9*48000)],98)*.45
    mask=(envelope>threshold)&gate
    mask[:int(1.1*48000)]=False
    edges=np.flatnonzero(np.diff(np.r_[False,mask,False]))
    groups=[];marks='';prev=None;timings=[]
    for start,end in edges.reshape(-1,2):
        duration=(end-start)/48000
        if duration<.025:continue
        if prev is not None and (start-prev)/48000>.12:
            groups.append(marks);marks=''
        marks+='-' if duration>.12 else '.'
        timings.append({'start_s':start/48000,'duration_s':duration})
        prev=end
    groups.append(marks)
    callsign=''.join(MORSE.get(g,'?') for g in groups)
    assert callsign=='KI5YNG',(folder,callsign,groups)
    pcm=np.clip(fm/12000*32767,-32768,32767).astype('<i2')
    with wave.open(str(folder/'derived-fm.wav'),'wb') as w:
        w.setparams((1,2,48000,0,'NONE','not compressed'));w.writeframes(pcm.tobytes())
    row=dict(capture_id=folder.name,sequence=original['packets'][0]['sequence'],
        native_hex=original['packets'][0]['hex'],native_name=original['packets'][0]['decoded']['name'],
        native_bytes=len(bytes.fromhex(original['packets'][0]['hex'])),
        frame_bytes=101,baud=1200,packet_airtime_s=808/1200,
        channel_contrast_db=original['channel_contrast_db'],
        adc_rail_fraction=original['adc_rail_fraction'],
        cw_callsign=callsign,cw_groups=groups,cw_marks=timings)
    rows.append(row)
    plots.append((folder.name,power,envelope,threshold))
(HERE/'evidence/summary.json').write_text(json.dumps(rows,indent=2)+'\n')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
for label,power,envelope,threshold in plots:
    axes[0].plot(np.arange(len(power))*.01,10*np.log10(power+1e-20),label=label)
    axes[1].plot(np.arange(0,len(envelope),480)/48000,envelope[::480],label=label)
axes[0].set(ylabel='Channel power (dBFS)',title='Received 1200-baud EMBER-format packet followed by CW KI5YNG')
axes[1].set(xlabel='Capture time (seconds)',ylabel='800 Hz envelope (Hz)',ylim=(0,700),xlim=(0,8),
            title='CW identification recovered from tone/gap durations; first packet excluded')
for ax in axes:
    ax.grid(alpha=.25);ax.legend(fontsize=7)
dest=HERE.parent/'images';dest.mkdir(exist_ok=True)
fig.savefig(dest/'beacon-proof.png',dpi=150);plt.close(fig)
with (HERE/'evidence/SHA256SUMS').open('w') as f:
    for p in sorted((HERE/'evidence').glob('20*/*')):
        if p.is_file():f.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(HERE/'evidence'))+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='cw_marks'} for r in rows],indent=2))
