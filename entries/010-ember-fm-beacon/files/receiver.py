#!/usr/bin/env python3
"""Forced SSH command: short idle-only receive window, then native decode."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
CLIENT='satnogs_satnogs-client'
IMAGE='librespace/satnogs-client:2.1.2'
CAPTURE='ember-beacon-capture'
GUARD='ember-beacon-restore'

def run(args,**kw):
    return subprocess.run(args,check=True,**kw)

def docker(*args,**kw):
    return run(['sudo','-n','docker',*args],**kw)

def quiet(*args):
    return subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def say(kind,value):
    print(kind+' '+json.dumps(value,separators=(',',':')),flush=True)

def capture():
    with (HERE/'receive.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            say('SKIP',{'reason':'beacon receiver already busy'});return
        inspect=docker('inspect','--format','{{.State.Running}} {{.State.Paused}}',CLIENT,capture_output=True,text=True).stdout.strip()
        usb=Path('/dev/bus/usb')
        devices=[]
        # Read identity from sysfs rather than assuming the USB bus address.
        for d in Path('/sys/bus/usb/devices').glob('*'):
            if (d/'idVendor').exists() and (d/'idProduct').exists() and (d/'idVendor').read_text().strip()=='0bda' and (d/'idProduct').read_text().strip()=='2838':
                devices.append(usb/f'{int((d/"busnum").read_text()):03d}'/f'{int((d/"devnum").read_text()):03d}')
        if len(devices)!=1:raise RuntimeError('Expected one RTL-SDR')
        device=str(devices[0])
        if inspect!='true false' or quiet('sudo','-n','fuser',device).returncode==0:
            say('SKIP',{'reason':'station paused/stopped or SDR in use'});return
        processes=docker('top',CLIENT,'-eo','pid,comm',capture_output=True,text=True).stdout.splitlines()[1:]
        if any(x.split(maxsplit=1)[-1].strip()!='satnogs-client' for x in processes):
            say('SKIP',{'reason':'SatNOGS worker present'});return
        paused=False
        proc=None
        result=None
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        with tempfile.TemporaryDirectory(prefix='ember-beacon-',dir='/dev/shm') as scratch:
            tmp=Path(scratch)
            try:
                docker('pause',CLIENT,stdout=subprocess.DEVNULL);paused=True
                # A scheduled worker might have started between the idle check
                # and pause. Recheck frozen process list before reserving SDR.
                processes=docker('top',CLIENT,'-eo','pid,comm',capture_output=True,text=True).stdout.splitlines()[1:]
                if any(x.split(maxsplit=1)[-1].strip()!='satnogs-client' for x in processes):
                    say('SKIP',{'reason':'observation started during admission'});return
                recovery='docker rm -f ember-beacon-capture >/dev/null 2>&1; docker unpause satnogs_satnogs-client >/dev/null 2>&1 || true'
                run(['sudo','-n','systemd-run','--quiet','--collect','--unit='+GUARD,'--on-active=25s','/bin/sh','-c',recovery])
                with (tmp/'rtl.log').open('w') as log:
                    proc=subprocess.Popen(['sudo','-n','docker','run','--rm','--name',CAPTURE,'--network','none',
                        '--device',device,'-v',str(tmp)+':/capture','--entrypoint','/usr/bin/rtl_sdr',IMAGE,
                        '-f','446050000','-s','240000','-g','0.9','-n','2880000','/capture/rx.iq'],
                        stdout=log,stderr=subprocess.STDOUT)
                    deadline=time.monotonic()+8
                    while time.monotonic()<deadline:
                        if proc.poll() is not None:raise RuntimeError('RTL-SDR exited before readiness')
                        if 'Allocating' in (tmp/'rtl.log').read_text():break
                        time.sleep(.05)
                    else:raise RuntimeError('Receiver readiness timeout')
                    say('READY',{'capture_id':stamp,'duration_s':12,'target_hz':446000000})
                    if proc.wait(timeout=18):raise RuntimeError('RTL-SDR capture failed')
            finally:
                quiet('sudo','-n','docker','rm','-f',CAPTURE)
                if paused:docker('unpause',CLIENT,stdout=subprocess.DEVNULL)
                quiet('sudo','-n','systemctl','stop',GUARD+'.timer')
            docker('run','--rm','--network','none','-v',str(HERE)+':/app:ro','-v',str(tmp)+':/capture',
                   '-w','/app','--entrypoint','/usr/bin/python3',IMAGE,'radio.py','decode','/capture/rx.iq','/capture/result.json',
                   stdout=subprocess.DEVNULL,timeout=30)
            result=json.loads((tmp/'result.json').read_text())
            result.update(capture_id=stamp,station_resumed=True)
            proof=HERE/'proofs';proof.mkdir(exist_ok=True)
            if len(list(proof.glob('*/rx.iq')))<3:
                saved=proof/stamp;shutil.copytree(tmp,saved)
                result['proof_saved']=True
            else:result['proof_saved']=False
            with (HERE/'results.jsonl').open('a') as out:
                out.write(json.dumps(result,separators=(',',':'))+'\n')
            say('RESULT',result)

if __name__=='__main__':
    if os.environ.get('SSH_ORIGINAL_COMMAND','capture')!='capture':
        raise SystemExit('Only capture is permitted')
    try:capture()
    except Exception as e:
        say('ERROR',{'error':str(e)});raise
