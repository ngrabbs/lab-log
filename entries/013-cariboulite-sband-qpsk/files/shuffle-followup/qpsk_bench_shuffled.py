"""Generate and decode the conducted CaribouLite science-frame experiment."""
import argparse
import csv
import json
import struct
import zlib
from pathlib import Path

import numpy as np
from scipy import optimize, signal

TX_FS = 2_000_000
RX_FS = 8_000_000
RX_OFFSET = 500_000
TX_FREQ = 2_250_000_000
RX_CENTER = TX_FREQ - RX_OFFSET
BETA = 0.35
SPAN = 12
TONE = 64
PILOT_LEN = 128
PAYLOAD = 512
FRAMES = 256
FRAME_BYTES = 4 + PAYLOAD + 4
FRAME_SYMBOLS = TONE + PILOT_LEN + FRAME_BYTES * 4
LEAD = 400_000
DMA_SAMPLES = 131_072
PILOT_SEED = 225001
SCIENCE_SEED = 225002
RMS_COUNTS = 12000


def qpsk(bits):
    signs = 1 - 2 * bits.reshape(-1, 2).astype(np.float32)
    return (signs[:, 0] + 1j * signs[:, 1]) / np.sqrt(np.float32(2))


PILOT = qpsk(np.random.default_rng(PILOT_SEED).integers(0, 2, 2 * PILOT_LEN, dtype=np.uint8))
def science_payloads(seed):
    return np.random.default_rng(seed).integers(0, 256, (FRAMES, PAYLOAD), dtype=np.uint8)


def sequence_order(seed):
    return np.arange(FRAMES) if seed is None else np.random.default_rng(seed).permutation(FRAMES)


def rrc(sps):
    t = np.arange(-SPAN * sps // 2, SPAN * sps // 2 + 1) / sps
    h = np.empty_like(t)
    zero = np.isclose(t, 0)
    singular = np.isclose(abs(t), 1 / (4 * BETA))
    ordinary = ~(singular | zero)
    tt = t[ordinary]
    h[ordinary] = (np.sin(np.pi * tt * (1 - BETA)) + 4 * BETA * tt * np.cos(np.pi * tt * (1 + BETA))) / (
        np.pi * tt * (1 - (4 * BETA * tt) ** 2))
    h[zero] = 1 + BETA * (4 / np.pi - 1)
    h[singular] = BETA / np.sqrt(2) * (
        (1 + 2 / np.pi) * np.sin(np.pi / (4 * BETA)) +
        (1 - 2 / np.pi) * np.cos(np.pi / (4 * BETA)))
    return (h / np.linalg.norm(h)).astype(np.float32)


def frame(seq, payloads):
    content = struct.pack('<I', seq) + payloads[seq].tobytes()
    return content + struct.pack('<I', zlib.crc32(content))


def generate(rate, path, payload_seed, order_seed):
    payloads = science_payloads(payload_seed)
    order = sequence_order(order_seed)
    sps = TX_FS // rate
    symbols = np.empty((FRAMES, FRAME_SYMBOLS), dtype=np.complex64)
    symbols[:, :TONE] = (1 + 1j) / np.sqrt(2)
    symbols[:, TONE:TONE + PILOT_LEN] = PILOT
    for j, seq in enumerate(order):
        symbols[j, TONE + PILOT_LEN:] = qpsk(np.unpackbits(np.frombuffer(frame(seq, payloads), dtype=np.uint8)))
    wave = signal.upfirdn(rrc(sps), symbols.ravel(), up=sps).astype(np.complex64)
    active_duration = FRAMES * FRAME_SYMBOLS / rate
    wave *= RMS_COUNTS / np.sqrt(np.mean(abs(wave) ** 2))
    iq = np.rint(np.column_stack([wave.real, wave.imag]))
    assert np.max(abs(iq)) < 24000
    peak = float(np.max(abs(wave)))
    iq = np.pad(iq, ((LEAD, LEAD), (0, 0)))
    iq = np.pad(iq, ((0, -len(iq) % DMA_SAMPLES), (0, 0))).astype('<i2')
    iq.tofile(path)
    print(json.dumps({
        'symbol_rate': rate, 'tx_rate': TX_FS, 'samples_per_symbol': sps,
        'frames': FRAMES, 'symbols_per_frame': FRAME_SYMBOLS, 'payload_bytes': PAYLOAD,
        'sequence_bytes': 4, 'crc_bytes': 4, 'tone_symbols': TONE, 'pilot_symbols': PILOT_LEN,
        'rolloff': BETA, 'rrc_span_symbols': SPAN, 'payload_seed': payload_seed,
        'order_seed': order_seed, 'sequence_at_position': order.tolist(),
        'pilot_seed': PILOT_SEED, 'packet_train_s': active_duration,
        'file_samples': len(iq), 'file_duration_s': len(iq) / TX_FS,
        'lead_and_tail_samples_each': LEAD, 'peak_envelope_counts': peak,
        'rms_envelope_counts': RMS_COUNTS,
        'scheduled_payload_bps': FRAMES * PAYLOAD * 8 / active_duration,
    }, indent=2))


def extract(path):
    raw = np.memmap(path, dtype=np.int8, mode='r').reshape(-1, 2)
    # Block size is a whole number of cycles at the receive LO offset.
    block = 320000
    oscillator = np.exp(-2j * np.pi * RX_OFFSET / RX_FS * np.arange(block)).astype(np.complex64)
    output = np.empty((len(raw) + 3) // 4, np.complex64)
    clipped = 0
    for k in range(0, len(raw), block):
        part = raw[k:k+block]
        clipped += np.count_nonzero((part == -128) | (part == 127))
        x = part.astype(np.float32).view(np.complex64).ravel()
        # Pad block edges before decimation so boundaries remain quiet.
        pad_lo = max(0, k - 128)
        pad_hi = min(len(raw), k + len(x) + 128)
        padded = raw[pad_lo:pad_hi].astype(np.float32).view(np.complex64).ravel()
        rot = np.resize(oscillator, len(padded) + block)
        start = (pad_lo - k) % block
        y = signal.resample_poly(padded * rot[start:start+len(padded)], 1, 4)
        i = (k-pad_lo)//4
        output[k//4:(k+len(x)+3)//4] = y[i:i+(len(x)+3)//4]
    return output, clipped / (2 * len(raw))


def active_window(z):
    block = TX_FS // 1000 * 10
    power = np.mean(abs(z[:len(z)//block * block].reshape(-1, block))**2, axis=1)
    noise = np.median(power[:max(4, min(80, len(power)//8))])
    peak = np.percentile(power, 98)
    active = power > max(noise * 4, peak * .04)
    edges = np.flatnonzero(np.diff(np.r_[False, active, False])).reshape(-1, 2)
    events = [(a, b) for a, b in edges if b-a >= 12]
    if not events:
        raise ValueError(f'No sustained burst. Quiet/peak power {noise:.3f}/{peak:.3f}')
    a, b = max(events, key=lambda p: p[1]-p[0])
    offset = max(0, (a-8)*block)
    end = min(len(z), (b+8)*block)
    return offset, end, a*block/TX_FS, b*block/TX_FS, noise


def carrier(z):
    f, p = signal.welch(z, fs=TX_FS, nperseg=65536, noverlap=32768, return_onesided=False)
    f, p = np.fft.fftshift(f), np.fft.fftshift(p)
    region = np.flatnonzero(abs(f) < 125000)
    # Pilot tone and transmitter leakage share the same carrier frequency.
    k = region[np.argmax(p[region])]
    v = 10 * np.log10(p[k-1:k+2])
    d = .5 * (v[0]-v[2]) / (v[0]-2*v[1]+v[2])
    return float(f[k] + np.clip(d,-.6,.6) * (f[k+1]-f[k]))


def correlate(z, sps):
    impulse = np.zeros((PILOT_LEN-1)*sps+1, np.complex64)
    impulse[::sps] = PILOT
    outputs = []
    for conjugated in (False, True):
        candidate = z.conj() if conjugated else z
        magnitude = abs(signal.fftconvolve(candidate, impulse[::-1].conj(), mode='valid'))
        peaks, _ = signal.find_peaks(magnitude, distance=int(FRAME_SYMBOLS*sps*.83),
                                      height=float(np.max(magnitude))*.32)
        strength = np.sort(magnitude[peaks])[-FRAMES:]
        score = np.sum(strength)
        outputs.append((score, conjugated, candidate, magnitude, peaks))
    return max(outputs, key=lambda v:v[0])[1:]


def estimate_spacing(starts, nominal, sps):
    if len(starts) < 3:
        return float(sps)
    nominal_ids = np.rint((starts-starts[0])/nominal).astype(int)
    # A missed preamble does not become a change in symbol clock.
    delta = np.diff(starts)
    slots = np.diff(nominal_ids)
    keep = (slots > 0) & (abs(delta-nominal*slots) < nominal*.02)
    ratios = delta[keep] / slots[keep] / FRAME_SYMBOLS
    if len(ratios) < 3:
        return float(sps)
    return float(np.median(ratios))


def phase_track(preamble, rate):
    index = np.arange(PILOT_LEN)
    design = np.column_stack([PILOT, PILOT.conj(), np.ones(PILOT_LEN)])

    def fit(hz):
        corrected = preamble * np.exp(-2j*np.pi*hz*index/rate)
        gain, image, dc = np.linalg.lstsq(design, corrected, rcond=None)[0]
        residual = np.mean(abs(corrected - design @ [gain, image, dc])**2)
        return residual, gain, image, dc

    result = optimize.minimize_scalar(lambda hz: fit(hz)[0], bounds=(-180,180),
                                      method='bounded', options={'xatol':.03})
    hz = float(result.x)
    _, gain, image, dc = fit(hz)
    calibration = hz, gain, image, dc
    calibrated = equalize(preamble, index, rate, calibration)
    evm = np.sqrt(np.mean(abs(calibrated - PILOT)**2))
    return calibration, float(evm)


def equalize(samples, pos, rate, calibration):
    hz, gain, image, dc = calibration
    y = samples * np.exp(-2j*np.pi*hz*pos/rate) - dc
    determinant = abs(gain)**2 - abs(image)**2
    if abs(determinant) < 1e-8:
        return np.full(len(samples),np.nan+1j*np.nan)
    return (gain.conjugate()*y-image*y.conj())/determinant


def track_payload_phase(value):
    # Gray QPSK has s**4 = -1. Smooth the fourth power to recover
    # residual phase drift without consulting the data or the CRC.
    normalized = value / np.maximum(abs(value), .5)
    smooth = signal.convolve(-(normalized**4), np.hanning(129)/64, mode='same')
    rotation = np.unwrap(np.angle(smooth)) / 4
    pilot_offset = np.angle(np.vdot(PILOT, value[:PILOT_LEN]*np.exp(-1j*rotation[:PILOT_LEN])))
    ambiguity = round(pilot_offset/(np.pi/2))*np.pi/2
    return value * np.exp(-1j*(rotation+ambiguity))


def write_folded_errors(out, observations, valid, order, payloads, spacing, sps):
    # Offline diagnostic only. Ground-truth bytes do not feed the demodulator.
    period = 32768
    bin_samples = 256
    n_bins = period // bin_samples
    position = np.argsort(order)
    frame_s = spacing * FRAME_SYMBOLS / TX_FS
    anchor = np.median([t - position[seq] * frame_s for seq, (t, _) in valid.items()])
    symbol_offset = (TONE + PILOT_LEN + np.arange(FRAME_BYTES * 4)) * sps
    fixed_delay = LEAD + SPAN * sps // 2
    counted = np.zeros(n_bins, dtype=np.int64)
    errors = np.zeros(n_bins, dtype=np.int64)
    used_slots = set()
    for start_s, observed in observations:
        estimate = (start_s - anchor) / frame_s
        slot = round(estimate)
        if not 0 <= slot < FRAMES or abs(estimate - slot) >= .1 or slot in used_slots:
            continue
        used_slots.add(slot)
        expected = frame(order[slot], payloads)
        xor = np.frombuffer(observed, dtype=np.uint8) ^ np.frombuffer(expected, dtype=np.uint8)
        bit_errors = np.unpackbits(xor).reshape(-1, 2).sum(axis=1).astype(np.int64)
        sample_index = fixed_delay + slot * FRAME_SYMBOLS * sps + symbol_offset
        phase_bins = (sample_index % period) // bin_samples
        np.add.at(counted, phase_bins, 2)
        np.add.at(errors, phase_bins, bit_errors)
    with (out / 'errors-by-dma-phase.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['phase_start_tx_samples', 'phase_end_tx_samples', 'bits_compared', 'bit_errors'])
        for j in range(n_bins):
            writer.writerow([j * bin_samples, (j + 1) * bin_samples, counted[j], errors[j]])


def make_decode(rate, path, out, payload_seed, order_seed, diagnose_dma=False):
    payloads = science_payloads(payload_seed)
    order = sequence_order(order_seed)
    sps = TX_FS // rate
    z, clip = extract(path)
    offset, stop, rf_start, rf_end, noise = active_window(z)
    z = z[offset:stop]
    cfo = carrier(z)
    z *= np.exp(-2j*np.pi*cfo/TX_FS*np.arange(len(z))).astype(np.complex64)
    z = signal.fftconvolve(z, rrc(sps), mode='same')
    conj, data, correlation, peaks = correlate(z, sps)
    magnitude = correlation
    good_peaks = peaks[(peaks>0)&(peaks<len(magnitude)-1)]
    left, mid, right = magnitude[good_peaks-1],magnitude[good_peaks],magnitude[good_peaks+1]
    with np.errstate(invalid='ignore',divide='ignore'):
        fraction=.5*(left-right)/(left-2*mid+right)
    starts=good_peaks+np.nan_to_num(fraction).clip(-.6,.6)
    spacing=estimate_spacing(starts,FRAME_SYMBOLS*sps,sps)
    pos=np.arange(PILOT_LEN + FRAME_BYTES * 4)
    # `interp` only touches each local frame slice.
    rows=[]
    valid={}
    observations=[]
    for start,peak in zip(starts,good_peaks):
        indices=start+spacing*pos
        a=int(indices[0])-1
        b=int(indices[-1])+3
        if a<0 or b>len(data):
            continue
        local=data[a:b]
        grid=np.arange(len(local))
        samples=np.interp(indices-a,grid,local.real)+1j*np.interp(indices-a,grid,local.imag)
        calibration,evm=phase_track(samples[:PILOT_LEN], rate)
        hz,gain,image,dc=calibration
        value=track_payload_phase(equalize(samples, pos, rate, calibration))
        bits=(np.column_stack([value[PILOT_LEN:].real, value[PILOT_LEN:].imag])<0).astype(np.uint8)
        packet=np.packbits(bits.ravel()).tobytes()
        seq=struct.unpack_from('<I',packet)[0]
        crc_ok=zlib.crc32(packet[:-4])==struct.unpack_from('<I',packet,len(packet)-4)[0]
        known=crc_ok and seq<FRAMES and packet==frame(seq, payloads)
        start_s=(offset+start-TONE*spacing)/TX_FS
        if diagnose_dma:
            observations.append((start_s, packet))
        duplicate=known and seq in valid
        if known and not duplicate:
            valid[seq]=(start_s,evm)
        rows.append({
            'frame_start_s': start_s,'detected_sequence': seq,'crc_ok': int(crc_ok),
            'payload_matches':int(known),'duplicate':int(duplicate),'pilot_evm_pct':evm*100,
            'pilot_cfo_residual_hz':hz,'sync_peak':float(magnitude[peak]),
            'image_relative_db':20*np.log10(max(abs(image)/max(abs(gain),1e-12),1e-12)),
            'carrier_leakage_relative_db':20*np.log10(max(abs(dc)/max(abs(gain),1e-12),1e-12)),
        })
    with (out/'detections.csv').open('w',newline='') as f:
        names=['frame_start_s','detected_sequence','crc_ok','payload_matches','duplicate','pilot_evm_pct','pilot_cfo_residual_hz','sync_peak','image_relative_db','carrier_leakage_relative_db']
        writer=csv.DictWriter(f,fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)
    with (out/'frames.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['position','sequence','crc_and_payload_ok','frame_start_s','pilot_evm_pct'])
        for position, seq in enumerate(order):
            if seq in valid:
                t,e=valid[seq]
                writer.writerow([position,seq,1,round(t,8),round(e*100,4)])
            else:
                writer.writerow([position,seq,0,'',''])
    nominal_s=FRAMES*FRAME_SYMBOLS/rate
    delivered=len(valid)*PAYLOAD*8
    summary={
        'symbol_rate':rate,'expected_frames':FRAMES,'valid_unique_frames':len(valid),
        'lost_frames':FRAMES-len(valid),'packet_loss_pct':100*(FRAMES-len(valid))/FRAMES,
        'payload_bytes_delivered':len(valid)*PAYLOAD,'bad_crc_candidates':sum(not row['crc_ok'] for row in rows),
        'duplicate_frames':sum(row['duplicate'] for row in rows),
        'scheduled_packet_train_s':nominal_s,
        'payload_goodput_bps':delivered/nominal_s,
        'rf_start_s_10ms':rf_start,'rf_end_s_10ms':rf_end,
        'whole_burst_goodput_bps_10ms':delivered/(rf_end-rf_start),
        'coarse_carrier_residual_hz':cfo,'iq_conjugated':bool(conj),
        'effective_samples_per_symbol':spacing,'adc_component_clip_fraction':clip,
        'median_pilot_evm_pct':float(np.median([v[1] for v in valid.values()])*100) if valid else None,
        'noise_energy_adc_counts_sq':float(noise)
    }
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if diagnose_dma and valid:
        write_folded_errors(out, observations, valid, order, payloads, spacing, sps)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['generate','decode'])
    p.add_argument('symbol_rate',type=int,choices=[250000,500000])
    p.add_argument('path',type=Path)
    p.add_argument('--out',type=Path,default=Path('.'))
    p.add_argument('--payload-seed', type=int, default=SCIENCE_SEED)
    p.add_argument('--order-seed', type=int)
    p.add_argument('--diagnose-dma', action='store_true')
    args=p.parse_args()
    if args.mode=='generate':
        generate(args.symbol_rate,args.path,args.payload_seed,args.order_seed)
    else:
        args.out.mkdir(parents=True,exist_ok=True)
        make_decode(args.symbol_rate,args.path,args.out,args.payload_seed,args.order_seed,args.diagnose_dma)
