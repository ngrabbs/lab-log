"""EMBER v3 frames over an FM audio link. Not a native RF BPSK modem."""
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'vendor/ground/ember'))
from codec import encode, decode
spec = importlib.util.spec_from_file_location('ember_native_modem', HERE / 'vendor/ground/bpsk/modem.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
FS = 48000
BAUD = 1200
MORSE = {'K':'-.-','I':'..','5':'.....','Y':'-.--','N':'-.','G':'--.'}


def identity():
    candidates = []
    for p in Path('/sys/class/hidraw').glob('hidraw*'):
        if 'HID_ID=0003:00000D8C:00000012' in (p/'device/uevent').read_text():
            candidates.append('/dev/' + p.name)
    if len(candidates) != 1:
        raise RuntimeError('Expected exactly one Digirig Lite HID device')
    return candidates[0]


def release():
    with open(identity(), 'wb', buffering=0) as f:
        if f.write(bytes([0,0,0,4,0])) != 5:
            raise RuntimeError('Incomplete PTT release')


def waveform(packet, sequence, callsign='KI5YNG', amplitude=.03):
    frame = native.frame(packet, sequence)
    b = np.unpackbits(np.frombuffer(frame, dtype=np.uint8)).astype(float)
    phase = np.cumprod(1-2*b)
    env = np.repeat(phase, FS//BAUD)
    kernel = np.hanning(9)
    env = np.convolve(env, kernel/kernel.sum(), mode='same')
    data = amplitude*env*np.cos(2*np.pi*1500*np.arange(len(env))/FS)
    chunks = [np.zeros(int(.05*FS)), amplitude*np.cos(2*np.pi*1500*np.arange(int(.1*FS))/FS),
              data, np.zeros(int(.15*FS))]
    # Identification is an audible 800 Hz CW callsign at 20 WPM, after the packet.
    for letter in callsign:
        for mark in MORSE[letter]:
            n = round(FS*.06*(3 if mark=='-' else 1))
            tone = amplitude*np.cos(2*np.pi*800*np.arange(n)/FS)
            ramp = np.minimum(1, np.minimum(np.arange(n)/240, np.arange(n)[::-1]/240))
            chunks.extend([tone*ramp, np.zeros(round(FS*.06))])
        chunks.append(np.zeros(round(FS*.12)))
    chunks.append(np.zeros(int(.15*FS)))
    return np.concatenate(chunks), frame


def make_packet(sequence, boot, uptime_ms):
    # Deliberate source=COMMS emulation for this ground-test beacon. These are
    # Pi boot/uptime values, NOT measurements received from the Pico or IHU.
    return encode('HEARTBEAT', sequence=sequence % 16384, source=3, target=1,
                  source_boot_id=boot, uptime_ms=uptime_ms % (2**32),
                  payload={'mode':2, 'configuration':1, 'telemetry_period_ms':120000})


def save_wave(path, audio):
    stereo = np.column_stack([np.round(audio*32767).astype('<i2'), np.zeros(len(audio), dtype='<i2')])
    with wave.open(str(path), 'wb') as w:
        w.setparams((2,2,FS,0,'NONE','not compressed'))
        w.writeframes(stereo.tobytes())


def transmit(path):
    hid = identity()
    with wave.open(str(path)) as w:
        assert w.getnchannels()==2 and w.getframerate()==FS and w.getsampwidth()==2
        duration = w.getnframes()/FS
    if not 0 < duration < 10:
        raise RuntimeError('Beacon WAV must be shorter than ten seconds')
    # Separate release process verifies the HID identity again before writing.
    watchdog = subprocess.Popen([sys.executable, '-c',
        'import time,radio; time.sleep(float(__import__("sys").argv[1])); radio.release()', str(duration+2)],
        cwd=HERE, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True)
    on = None
    try:
        with open(hid,'wb',buffering=0) as f:
            f.write(bytes([0,0,0,4,0]))
            if f.write(bytes([0,0,4,4,0])) != 5:
                raise RuntimeError('Incomplete PTT assertion')
        on = time.time()
        time.sleep(.3)
        subprocess.run(['aplay','-q','-D','plughw:CARD=Device,DEV=0',str(path)],
                       check=True, timeout=duration+1)
    finally:
        release()
    off = time.time()
    if watchdog.wait(timeout=5):
        raise RuntimeError('Backup PTT release failed')
    return {'ptt_on_epoch':on, 'ptt_off_epoch':off, 'ptt_seconds':off-on,
            'audio_seconds':duration, 'hid':hid}


def receive(path):
    from scipy import signal
    raw = np.fromfile(path,dtype=np.uint8)
    x = ((raw[::2].astype(float)-127.5)+1j*(raw[1::2].astype(float)-127.5))/127.5
    x *= np.exp(2j*np.pi*50000*np.arange(len(x))/240000)
    channel = signal.sosfilt(signal.butter(6,10000,fs=240000,output='sos'),x)
    bb = signal.resample_poly(channel,1,5)
    fm = np.angle(bb[1:]*bb[:-1].conj())*FS/(2*np.pi)
    audio = signal.sosfiltfilt(signal.butter(4,[300,3000],btype='bandpass',fs=FS,output='sos'),fm)
    base = audio*np.exp(-2j*np.pi*1500*np.arange(len(audio))/FS)
    base = signal.sosfiltfilt(signal.butter(4,1100,fs=FS,output='sos'),base)
    noise = float(np.mean(abs(channel[-240000:])**2))
    powers = np.mean(abs(channel[:len(channel)//2400*2400].reshape(-1,2400))**2,axis=1)
    hits = np.flatnonzero((powers > noise*10) & (np.arange(len(powers))>=10))
    start = max(0,float(hits[0])*.01-.05) if len(hits) else 0
    # Packet precedes CW identification. Exclude the longer 800 Hz ID from the
    # canonical decoder's squaring-based carrier acquisition.
    segment = base[round(start*FS):round((start+1.5)*FS)]
    packets = native.decode(segment,FS,single_window=True)
    on = float(np.mean(abs(channel[round(start*240000):round((start+1.5)*240000)])**2))
    return dict(mode='EMBER-v3-DBPSK1200-audio-over-FM', callsign='KI5YNG',
                bench_source_emulated=True, sample_rate=240000, center_hz=446050000,
                target_hz=446000000, baud=1200, duration_s=len(x)/240000,
                adc_rail_fraction=float(np.mean((raw<=1)|(raw>=254))),
                rf_onset_estimate_s=start, channel_on_dbfs=10*math.log10(max(on,1e-20)),
                channel_off_dbfs=10*math.log10(max(noise,1e-20)),
                channel_contrast_db=10*math.log10(max(on,1e-20)/max(noise,1e-20)),
                packets=packets)


if __name__=='__main__':
    if sys.argv[1]=='release':
        release()
    elif sys.argv[1]=='decode':
        result = receive(sys.argv[2])
        Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result, separators=(',',':')),flush=True)
    elif sys.argv[1]=='selftest':
        packet=make_packet(1,123,456789)
        audio,frame=waveform(packet,1)
        assert len(packet)==38 and len(frame)==101
        from scipy import signal
        base=signal.sosfiltfilt(signal.butter(4,1100,fs=FS,output='sos'),
            audio*np.exp(-2j*np.pi*1500*np.arange(len(audio))/FS))
        recovered=native.decode(base[:int(1.1*FS)],FS,single_window=True)
        assert len(recovered)==1 and recovered[0]['hex']==packet.hex(), recovered
        bad=bytearray(packet);bad[-1]^=1
        try:decode(bytes(bad))
        except ValueError:pass
        else:raise AssertionError('Bad CRC accepted')
        print('PASS: canonical native frame/CRC and 1200-baud audio loopback')
