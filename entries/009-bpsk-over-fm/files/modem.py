#!/usr/bin/env python3
"""Experimental 100 bit/s differential BPSK audio packets, carried over FM.

This is a custom bench format, not PSK31 or a compatible standard modem.
Wire order: 64 training bits, 32-bit sync, version/u16 sequence/u16 length,
UTF-8 payload, CRC32(header+payload). Bytes and bits are big endian.
"""
import argparse
import json
import struct
import wave
import zlib
from pathlib import Path

import numpy as np

FS = 48000
BAUD = 100
CARRIER = 1500
SYNC = bytes.fromhex('1acffc1d')


def bits(data):
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def make_wave(message, count=3, amplitude=0.1):
    chunks = [np.zeros(FS // 2)]
    packets = []
    for seq in range(1, count + 1):
        payload = message.encode('utf-8')
        header = struct.pack('>BHH', 1, seq, len(payload))
        body = header + payload
        frame = body + struct.pack('>I', zlib.crc32(body))
        b = np.r_[np.tile([0, 1], 32), bits(SYNC + frame)]
        # 1 flips phase; 0 preserves it. Smooth each sign change over ~1 ms.
        phase = np.cumprod(1 - 2 * b.astype(float))
        envelope = np.repeat(phase, FS // BAUD)
        kernel = np.hanning(49)
        envelope = np.convolve(envelope, kernel / kernel.sum(), mode='same')
        t = np.arange(len(envelope)) / FS
        audio = amplitude * envelope * np.cos(2 * np.pi * CARRIER * t)
        packets.append(dict(sequence=seq, payload=message,
                            payload_bytes=len(payload), frame_bits=len(b),
                            waveform_start_s=sum(map(len, chunks)) / FS,
                            waveform_duration_s=len(audio) / FS,
                            crc32=f'{zlib.crc32(body):08x}'))
        chunks.extend([audio, np.zeros(FS // 5)])
    chunks.append(np.zeros(FS // 5))
    return np.concatenate(chunks), packets


def decode_audio(audio):
    from scipy import signal
    # Mix to complex baseband, anti-alias filter, and reduce to 6 ksample/s.
    t = np.arange(len(audio)) / FS
    base = signal.resample_poly(audio * np.exp(-2j * np.pi * CARRIER * t), 1, 8)
    base = signal.sosfiltfilt(signal.butter(4, 250, fs=6000, output='sos'), base)
    sps = 6000 // BAUD
    sync_bits = bits(SYNC)
    pattern = 1 - 2 * sync_bits.astype(float)
    found = {}
    for offset in range(sps):
        x = base[offset:]
        n = len(x) // sps
        if n < 100:
            continue
        symbols = x[:n * sps].reshape(n, sps).mean(axis=1)
        product = symbols[1:] * symbols[:-1].conj()
        decoded = (product.real < 0).astype(np.uint8)
        corr = np.correlate(1 - 2 * decoded.astype(float), pattern, 'valid')
        for start in np.flatnonzero(corr >= 28):  # <=2 sync bit errors
            begin = start + 32
            header_bits = decoded[begin:begin + 40]
            if len(header_bits) != 40:
                continue
            header = np.packbits(header_bits).tobytes()
            version, seq, length = struct.unpack('>BHH', header)
            if version != 1 or not 0 < length <= 256:
                continue
            end = begin + (5 + length + 4) * 8
            if end > len(decoded):
                continue
            raw = np.packbits(decoded[begin:end]).tobytes()
            expected = struct.unpack('>I', raw[-4:])[0]
            if zlib.crc32(raw[:-4]) != expected:
                continue
            result = dict(sequence=seq, payload=raw[5:-4].decode('utf-8', 'replace'),
                          payload_bytes=length, crc32=f'{expected:08x}', crc_ok=True,
                          sync_bit_errors=int((32 - corr[start]) / 2),
                          sync_time_s=(offset + (start + 1) * sps) / 6000,
                          timing_offset_samples_6k=offset)
            # Differential phase coherence: diagnostic, not calibrated SNR.
            pp = product[begin:end]
            result['differential_coherence'] = float(np.mean(
                np.abs(pp.real) / np.maximum(np.abs(pp), 1e-20)))
            if seq not in found or result['differential_coherence'] > found[seq]['differential_coherence']:
                found[seq] = result
    return sorted(found.values(), key=lambda x: x['sequence'])


def receive(iq_path, sample_rate=240000, center=446050000, target=446000000):
    from scipy import signal
    raw = np.fromfile(iq_path, dtype=np.uint8)
    raw = raw[:len(raw) // 2 * 2]
    x = (raw[0::2].astype(np.float32) - 127.5 +
         1j * (raw[1::2].astype(np.float32) - 127.5)) / 127.5
    x *= np.exp(-2j * np.pi * (target - center) * np.arange(len(x)) / sample_rate)
    # 20 kHz-wide RF channel before the FM discriminator.
    channel = signal.sosfilt(signal.butter(6, 10000, fs=sample_rate, output='sos'), x)
    bb = signal.resample_poly(channel, 1, 5)
    fm_hz = np.angle(bb[1:] * bb[:-1].conj()) * FS / (2 * np.pi)
    audio = signal.sosfiltfilt(signal.butter(4, [300, 3000], btype='bandpass',
                                           fs=FS, output='sos'), fm_hz)
    # Store derived audio with a fixed scale: +/-12 kHz discriminator = full scale.
    pcm = np.clip(audio / 12000 * 32767, -32768, 32767).astype('<i2')
    with wave.open(str(Path(iq_path).with_suffix('.wav')), 'wb') as w:
        w.setparams((1, 2, FS, 0, 'NONE', 'not compressed'))
        w.writeframes(pcm.tobytes())
    packets = decode_audio(audio)
    blocks = []
    for i in range(len(channel) // sample_rate):
        segment = channel[i * sample_rate:(i + 1) * sample_rate]
        power = float(np.mean(np.abs(segment) ** 2))
        disc = fm_hz[i * FS:min((i + 1) * FS, len(fm_hz))]
        blocks.append(dict(second=i, channel_power_dbfs=10 * np.log10(max(power, 1e-20)),
                           fm_mean_hz=float(np.mean(disc)),
                           fm_rms_hz=float(np.std(disc))))
    return dict(iq_file=Path(iq_path).name, iq_format='interleaved unsigned 8-bit I,Q',
                sample_rate=sample_rate, center_hz=center, target_hz=target,
                duration_s=len(x) / sample_rate,
                adc_rail_fraction=float(np.mean((raw <= 1) | (raw >= 254))),
                rf_channel_bandwidth_hz=20000, packets=packets, seconds=blocks)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    tx = sub.add_parser('encode')
    tx.add_argument('--message', required=True)
    tx.add_argument('--count', type=int, default=3)
    tx.add_argument('--amplitude', type=float, default=0.1)
    tx.add_argument('--wav', default='tx.wav')
    rx = sub.add_parser('decode')
    rx.add_argument('iq')
    rx.add_argument('--json', default='rx.json')
    sub.add_parser('selftest')
    a = p.parse_args()
    if a.command == 'encode':
        assert 0 < a.amplitude <= 0.5 and 1 <= a.count <= 4
        x, packets = make_wave(a.message, a.count, a.amplitude)
        stereo = np.column_stack([np.round(x * 32767).astype('<i2'), np.zeros(len(x), dtype='<i2')])
        with wave.open(a.wav, 'wb') as w:
            w.setparams((2, 2, FS, 0, 'NONE', 'not compressed'))
            w.writeframes(stereo.tobytes())
        manifest = dict(message=a.message, baud=BAUD, audio_carrier_hz=CARRIER,
                        sample_rate=FS, digital_peak=a.amplitude, duration_s=len(x)/FS,
                        packets=packets)
        Path(a.wav).with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
        print(json.dumps(manifest, indent=2))
    elif a.command == 'decode':
        r = receive(a.iq)
        Path(a.json).write_text(json.dumps(r, indent=2)+'\n')
        print(json.dumps({k:v for k,v in r.items() if k!='seconds'}, indent=2))
    else:
        rng = np.random.default_rng(9009)
        x, _ = make_wave('OFFLINE SELFTEST', count=2)
        noisy = np.r_[np.zeros(137), -x + rng.normal(0, 0.02, len(x))]
        r = decode_audio(noisy)
        assert [q['sequence'] for q in r] == [1, 2], r
        assert all(q['payload']=='OFFLINE SELFTEST' for q in r)
        assert not decode_audio(rng.normal(0, 0.02, FS * 3))
        print('PASS: noisy delayed/inverted audio decodes; noise-only produces no packets')


if __name__ == '__main__':
    main()
