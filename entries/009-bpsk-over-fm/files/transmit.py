#!/usr/bin/env python3
"""Play a prepared stereo WAV through Digirig Lite with bounded GPIO3 PTT."""
import argparse
import os
import signal
import subprocess
import time
import wave
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('wav')
p.add_argument('--hid', default='/dev/hidraw0')
p.add_argument('--audio', default='plughw:CARD=Device,DEV=0')
a = p.parse_args()
with wave.open(a.wav) as w:
    assert w.getnchannels()==2 and w.getsampwidth()==2 and w.getframerate()==48000
    duration=w.getnframes()/w.getframerate()
assert 0 < duration <= 25, 'WAV must be at most 25 seconds'
uevent=Path('/sys/class/hidraw')/Path(a.hid).name/'device/uevent'
assert '00000D8C:00000012' in uevent.read_text(), 'Unexpected HID device'
fd=os.open(a.hid,os.O_WRONLY)
def ptt(on):
    if os.write(fd,bytes([0,0,4 if on else 0,4,0]))!=5:
        raise RuntimeError('Incomplete PTT report')
def stop(*_):
    raise SystemExit('Interrupted')
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
watchdog=None
try:
    ptt(False)
    # Independent process releases PTT even if the playback process dies.
    code='import sys,time,os; time.sleep(float(sys.argv[2])); f=os.open(sys.argv[1],os.O_WRONLY); os.write(f,bytes([0,0,0,4,0])); os.close(f)'
    watchdog=subprocess.Popen(['python3','-c',code,a.hid,str(duration+3)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    ptt(True)
    print('PTT ON',time.time(),flush=True)
    time.sleep(.3)
    subprocess.run(['aplay','-q','-D',a.audio,a.wav],check=True,timeout=duration+1)
finally:
    try:
        ptt(False)
        print('PTT OFF',time.time(),flush=True)
    finally:
        os.close(fd)
if watchdog:
    assert watchdog.wait(timeout=5)==0, 'Backup release failed'
