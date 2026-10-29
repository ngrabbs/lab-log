#!/usr/bin/env python3
"""One short, identified ground-test beacon; systemd schedules repetitions."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time

import radio

HERE=Path(__file__).resolve().parent
def interrupted(*_):raise SystemExit('Service stopped')
signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)

def main():
    cfg=json.loads((HERE/'config.json').read_text())
    assert cfg['callsign']=='KI5YNG' and cfg['frequency_hz']==446000000
    assert cfg['mode']=='EMBER-v3-DBPSK1200-audio-over-FM'
    if not (HERE/'ARMED').exists():raise SystemExit('Beacon is not armed')
    # Refuse before reserving the shared receiver if the local interface has
    # been unplugged or its HID permissions are missing.
    hid=radio.identity()
    if not os.access(hid,os.W_OK):raise RuntimeError('Digirig PTT is not writable')
    with (HERE/'transmit.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state_path=HERE/'state.json'
        seq=json.loads(state_path.read_text())['sequence']+1 if state_path.exists() else 1
        if seq>=2**32:raise RuntimeError('Sequence exhausted')
        state_path.write_text(json.dumps({'sequence':seq})+'\n')
        boot=int.from_bytes(hashlib.sha256(Path('/proc/sys/kernel/random/boot_id').read_bytes()).digest()[:4],'big') or 1
        uptime=int(float(Path('/proc/uptime').read_text().split()[0])*1000)
        packet=radio.make_packet(seq,boot,uptime)
        audio,frame=radio.waveform(packet,seq,cfg['callsign'],cfg['amplitude'])
        radio.save_wave(HERE/'current.wav',audio)
        result=dict(sequence=seq,callsign=cfg['callsign'],mode=cfg['mode'],bench_source_emulated=True,
                    native_hex=packet.hex(),frame_bytes=len(frame),baud=1200,
                    packet_airtime_s=len(frame)*8/1200,amplitude=cfg['amplitude'],
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat())
        # Receiver SSH key is command-restricted. No private key is published.
        proc=subprocess.Popen(['ssh','-i',str(HERE/'receiver_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
            '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(HERE/'known_hosts'),
            '-o','ConnectTimeout=5',cfg['receiver'],'capture'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            ready=False;diagnostics=[];deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                readable,_,_=select.select([proc.stdout],[],[],.5)
                if not readable:continue
                line=proc.stdout.readline()
                if not line:break
                diagnostics.append(line.strip())
                if line.startswith('SKIP '):
                    result.update(status='skipped',receiver=json.loads(line[5:]));break
                if line.startswith('READY '):
                    result['receiver_ready']=json.loads(line[6:]);ready=True;break
            if ready:
                result.update(radio.transmit(HERE/'current.wav'))
                remaining,err=proc.communicate(timeout=35)
                messages=[json.loads(x[7:]) for x in remaining.splitlines() if x.startswith('RESULT ')]
                if proc.returncode or len(messages)!=1:
                    raise RuntimeError('Receiver failed after transmission: '+err[-500:])
                result['receiver']=messages[0]
                matched=[p for p in messages[0]['packets'] if p['sequence']==seq and p['hex']==packet.hex()]
                result['status']='decoded' if matched else 'not-decoded'
            elif result.get('status')!='skipped':
                raise RuntimeError('Receiver did not become ready; no transmission started: '+'; '.join(diagnostics))
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
        with (HERE/'beacons.jsonl').open('a') as log:
            log.write(json.dumps(result,separators=(',',':'))+'\n')
        print(json.dumps(result,separators=(',',':')),flush=True)
        if result['status']=='not-decoded':raise SystemExit(2)

if __name__=='__main__':main()
