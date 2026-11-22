"""Summarize the crossed QPSK bench experiment from the archived run directories."""
import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import numpy as np

CONDITIONS = ('ordered-original', 'shuffled-original', 'ordered-fresh', 'shuffled-fresh')
RATES = (250000, 500000)


def read_csv(path, delimiter=','):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def compare(a, b):
    """Phi correlation of failures and the common failures above chance overlap."""
    aa, bb = a.astype(bool), b.astype(bool)
    total = len(aa)
    assert total == len(bb)
    both = int(np.count_nonzero(aa & bb))
    expected = np.count_nonzero(aa)*np.count_nonzero(bb)/total
    phi = float(np.corrcoef(aa, bb)[0, 1]) if np.std(aa) and np.std(bb) else None
    return {'positions_compared': total, 'common_failures': both,
            'common_failures_if_independent': expected, 'phi': phi}


def analyze(source, out):
    out.mkdir(parents=True, exist_ok=True)
    runs, frames, pairs, aggregates, detections, manifest = [], [], [], [], [], []
    patterns = {}
    by_dma_phase = []
    for row in read_csv(source/'schedule.tsv', delimiter='\t'):
        rate, repeat = int(row['symbol_rate']), int(row['repeat'])
        tag, condition, waveform = (row[k] for k in ('run', 'condition', 'waveform'))
        folder = source/tag
        info = json.loads((folder/'summary.json').read_text())
        tx = (folder/'tx-result.log').read_text()
        requested, accepted, partial, tx_elapsed = re.search(
            r'requested=(\d+) accepted=(\d+) partial=(\d+) elapsed=([\d.]+)', tx).groups()
        assert requested == accepted and partial == '0', tag
        frames_in_run = read_csv(folder/'frames.csv')
        preambles = read_csv(folder/'detections.csv')
        by_position = np.array([int(f['crc_and_payload_ok']) == 0 for f in frames_in_run])
        seq_at_pos = np.array([int(f['sequence']) for f in frames_in_run])
        assert len(by_position) == 256 and sorted(seq_at_pos.tolist()) == list(range(256)), tag
        assert np.count_nonzero(~by_position) == info['valid_unique_frames'], tag
        expected_positions = np.arange(256)
        assert all(int(f['position']) == i for i, f in enumerate(frames_in_run)), tag

        # Check decoded sequence positions independently against timestamps.
        # Fit intercept from accepted sequences and the clock from all detected pilots.
        clock = info['effective_samples_per_symbol'] * 2272 / 2_000_000
        valid = [f for f in frames_in_run if int(f['crc_and_payload_ok'])]
        anchor = median(float(f['frame_start_s'])-int(f['position'])*clock for f in valid)
        max_error = max(abs((float(f['frame_start_s'])-anchor)/clock-int(f['position'])) for f in valid)
        assert max_error < .1, (tag, max_error)
        found_slots = set()
        for detect in preambles:
            timing = (float(detect['frame_start_s'])-anchor)/clock
            slot = round(timing)
            if 0 <= slot < 256 and abs(timing-slot) < .1:
                found_slots.add(slot)
                assert not int(detect['payload_matches']) or int(detect['detected_sequence']) == seq_at_pos[slot]
            else:
                slot = ''
            detections.append({'run':tag, 'symbol_rate':rate, 'position_from_timing':slot, **detect})
        assert len(found_slots) >= len(valid), tag
        by_sequence = by_position[np.argsort(seq_at_pos)]
        patterns[rate, repeat, condition] = by_position, by_sequence, seq_at_pos
        start = (folder/'capture-start-utc.txt').read_text().strip()
        digest = (folder/'receive-sha256.txt').read_text().split()[0]
        metadata = {
            'global': {'core:datatype':'ci8', 'core:sample_rate':8000000, 'core:version':'1.2.0',
                       'core:hw':'HackRF One', 'core:description':(
                           f'{tag} at 2250 MHz through 30 dB pad. HackRF LNA/VGA 32/24 dB, port bias and RF amp off. '
                           f'2.5 MHz baseband filter. Capture command start UTC {start}, sample-zero time uncalibrated.')},
            'captures': [{'core:sample_start':0, 'core:frequency':2249500000}],
            'annotations': [],
        }
        (folder/'receive.sigmf-meta').write_text(json.dumps(metadata, indent=2)+'\n')
        manifest.append({**row, 'capture_cmd_start_utc':start, 'capture_bytes':120000000,
                         'receive_sha256':digest, 'sigmf_metadata':metadata})
        runs.append({**row, 'capture_cmd_start_utc':start, **info, 'preambles':len(preambles),
                     'preamble_slots':len(found_slots), 'max_valid_timing_error_in_slots':max_error,
                     'tx_requested_samples':requested, 'tx_accepted_samples':accepted,
                     'tx_partial_writes':partial, 'tx_write_s':tx_elapsed})
        folded = read_csv(folder/'errors-by-dma-phase.csv')
        assert len(folded) == 128
        assert sum(int(f['bits_compared']) for f in folded) == len(found_slots)*4160
        by_dma_phase.extend({'run':tag, 'symbol_rate':rate, 'condition':condition, **f} for f in folded)
        sps = 2_000_000 // rate
        for f in frames_in_run:
            position = int(f['position'])
            first = (400_000 + 6*sps + (2272*position + 192)*sps) % 32768
            overlaps = first < 256 or first + (2080-1)*sps >= 32768
            frames.append({'run':tag, 'symbol_rate':rate, 'condition':condition,
                           'preamble_at_position':int(position in found_slots),
                           'data_overlaps_first_dma_bin':int(overlaps), **f})

    for rate in RATES:
        for repeat in (1, 2, 3):
            p = {condition:patterns[rate, repeat, condition] for condition in CONDITIONS}
            for first, second, hold in (
                ('ordered-original', 'shuffled-original', 'payload'),
                ('ordered-fresh', 'shuffled-fresh', 'payload'),
                ('ordered-original', 'ordered-fresh', 'position'),
                ('shuffled-original', 'shuffled-fresh', 'position'),
                ('ordered-original', 'shuffled-fresh', 'neither'),
            ):
                a, b = p[first], p[second]
                for align, i in [('position', 0), ('sequence', 1)]:
                    # Exclude accidental fixed points when comparing shuffled to ordered.
                    # For position alignment also exclude those slots, where both keys agree.
                    fixed = a[2] == b[2]
                    if not np.all(fixed):
                        if i == 1:
                            fixed = np.isin(expected_positions, a[2][fixed])
                        aa, bb = a[i][~fixed], b[i][~fixed]
                    else:
                        aa, bb = a[i], b[i]
                    pairs.append({'symbol_rate':rate, 'repeat':repeat, 'first':first, 'second':second,
                                  'held_constant':hold, 'aligned_by':align, **compare(aa,bb)})
        for condition in CONDITIONS:
            selected = [r for r in runs if int(r['symbol_rate'])==rate and r['condition']==condition]
            assert len(selected)==3
            expected = sum(r['expected_frames'] for r in selected)
            delivered = sum(r['valid_unique_frames'] for r in selected)
            aggregates.append({'symbol_rate':rate, 'condition':condition, 'valid_frames':delivered,
                               'expected_frames':expected, 'packet_loss_pct':100*(expected-delivered)/expected,
                               'packet_train_goodput_bps':mean(r['payload_goodput_bps'] for r in selected),
                               'whole_burst_goodput_bps':mean(r['whole_burst_goodput_bps_10ms'] for r in selected)})

    write_csv(out/'run-summary.csv', runs)
    write_csv(out/'condition-summary.csv', aggregates)
    write_csv(out/'frame-outcomes.csv', frames)
    write_csv(out/'dma-phase-by-run.csv', by_dma_phase)
    folded_totals = defaultdict(lambda: [0, 0])
    for row in by_dma_phase:
        key = row['symbol_rate'], int(row['phase_start_tx_samples']), int(row['phase_end_tx_samples'])
        folded_totals[key][0] += int(row['bits_compared'])
        folded_totals[key][1] += int(row['bit_errors'])
    folded_summary = [
        {'symbol_rate':rate, 'phase_start_tx_samples':start, 'phase_end_tx_samples':end,
         'phase_midpoint_ms':(start+end)/4000, 'bits_compared':bits, 'bit_errors':errors,
         'ber':errors/bits}
        for (rate, start, end), (bits,errors) in sorted(folded_totals.items())
    ]
    write_csv(out/'dma-phase-summary.csv', folded_summary)
    for rate in RATES:
        folded_rate = [r for r in folded_summary if r['symbol_rate']==rate]
        peak = max(folded_rate, key=lambda r: r['ber'])
        print('DMA phase', rate, 'peak', peak['phase_midpoint_ms'], peak['ber'],
              'total errors', sum(r['bit_errors'] for r in folded_rate))
    write_csv(out/'preamble-detections.csv', detections)
    write_csv(out/'failure-agreement.csv', pairs)
    (out/'capture-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    waveforms = {m.stem:json.loads(m.read_text()) for m in sorted((source/'waveforms').glob('*.json'))}
    for line in (source/'waveforms'/'sha256.txt').read_text().splitlines():
        sha, filename = line.split()
        waveforms[Path(filename).stem]['sha256_cs16'] = sha
    (out/'waveform-manifest.json').write_text(json.dumps(waveforms, separators=(',', ':'))+'\n')
    for rate in RATES:
        for first, second in sorted({(r['first'],r['second']) for r in pairs}):
            matched = [r for r in pairs if r['symbol_rate']==rate and r['first']==first and r['second']==second]
            scores = {key:mean(x['phi'] for x in matched if x['aligned_by']==key and x['phi'] is not None)
                      for key in ('position','sequence')}
            print(rate, first, second, scores)
    for r in aggregates:
        print(r['symbol_rate'], r['condition'], r['valid_frames'], round(r['packet_loss_pct'], 2),
              round(r['packet_train_goodput_bps']/1000, 2), round(r['whole_burst_goodput_bps']/1000, 2))
    for rate in RATES:
        for crosses in (0,1):
            selected = [f for f in frames if f['symbol_rate']==rate and f['data_overlaps_first_dma_bin']==crosses]
            losses = sum(not int(f['crc_and_payload_ok']) for f in selected)
            print('DMA overlap', rate, crosses, losses, '/', len(selected))
    print('Preambles in scheduled slots', sum(r['preamble_slots'] for r in runs), '/', len(frames))
    print('Largest ADC rail fraction', max(r['adc_component_clip_fraction'] for r in runs))


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('capture', type=Path)
    cli.add_argument('out', type=Path)
    args = cli.parse_args()
    analyze(args.capture, args.out)
