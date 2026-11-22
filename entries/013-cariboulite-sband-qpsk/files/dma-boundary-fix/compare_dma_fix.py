"""Compare matched conducted QPSK captures before and after the TX DMA fix."""
import argparse
import csv
import json
from pathlib import Path
import re
from collections import defaultdict
from statistics import mean


def read_table(path, delimiter=','):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_table(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def phase_of(position, rate):
    sps = 2_000_000 // rate
    first = (400_000 + (6 + 2272*position + 192)*sps) % 32768
    return first < 256 or first + (2080-1)*sps >= 32768


def report(schedule, before, recorded, out):
    out.mkdir(parents=True, exist_ok=True)
    runs, frames, aggregate, phase_by_run, phases, manifest = [], [], [], [], [], []
    folders = {'before':before, **{s:recorded/s for s in ('control','smoke','after')}}
    phase_counts = defaultdict(lambda: [0, 0])
    for row in read_table(schedule, '\t'):
        tag, rate = row['run'], int(row['symbol_rate'])
        for stage, root in folders.items():
            folder = root/tag
            if not folder.is_dir():
                assert stage in ('control','smoke'), (tag, stage)
                continue
            summary = json.loads((folder/'summary.json').read_text())
            outcomes = read_table(folder/'frames.csv')
            detections = read_table(folder/'detections.csv')
            dma = read_table(folder/'errors-by-dma-phase.csv')
            assert len(outcomes)==len(detections)==summary['expected_frames']==256, (stage,tag)
            assert sum(int(f['crc_and_payload_ok']) for f in outcomes)==summary['valid_unique_frames']
            assert sum(int(r['bits_compared']) for r in dma)==256*4160
            sample_log = (folder/'tx-result.log').read_text()
            req, accepted, short = re.search(r'requested=(\d+) accepted=(\d+) partial=(\d+)', sample_log).groups()
            assert req==accepted and short=='0'
            run = {'stage':stage, **row, **summary, 'preambles':len(detections), 'tx_accepted_iq_samples':accepted,
                   'tx_partial_writes':short, 'capture_cmd_start_utc':(folder/'capture-start-utc.txt').read_text().strip()}
            runs.append(run)
            for f in outcomes:
                overlap = phase_of(int(f['position']), rate)
                frames.append({'stage':stage, 'run':tag, 'symbol_rate':rate, 'data_overlaps_first_period_bin':int(overlap), **f})
            for data in dma:
                phase_by_run.append({'stage':stage,'run':tag,'symbol_rate':rate,**data})
                phase = int(data['phase_start_tx_samples'])
                key = stage, rate, phase
                phase_counts[key][0] += int(data['bits_compared'])
                phase_counts[key][1] += int(data['bit_errors'])
            digest = (folder/'receive-sha256.txt').read_text().split()[0]
            if stage=='before':
                sigmf = json.loads((folder/'receive.sigmf-meta').read_text())
            else:
                sigmf = {
                    'global': {'core:datatype':'ci8', 'core:sample_rate':8_000_000, 'core:version':'1.2.0',
                               'core:hw':'HackRF One', 'core:description':(
                                   f'{stage}/{tag}. Conducted CaribouLite 2250 MHz, 30 dB pad, '
                                   f'min TX PA. RX LNA/VGA 32/24 dB, RF amp and bias off. '
                                   f'Command start UTC {run["capture_cmd_start_utc"]}. Sample-zero time uncalibrated.')},
                    'captures':[{'core:sample_start':0,'core:frequency':2249500000}],
                    'annotations':[],
                }
                (folder/'receive.sigmf-meta').write_text(json.dumps(sigmf, indent=2)+'\n')
            assert (folder/'receive.sigmf-data').stat().st_size==120_000_000
            manifest.append({'stage':stage, **row,'receive_sha256':digest,'receive_bytes':120_000_000,'sigmf_metadata':sigmf})

    assert len(runs)==15 and len(frames)==15*256
    for (stage, rate, phase), (bits, errors) in sorted(phase_counts.items()):
        phases.append({'stage':stage,'symbol_rate':rate,'phase_start_tx_samples':phase,
                       'phase_center_ms':(phase+128)/2000,'bits_compared':bits,'bit_errors':errors,'ber':errors/bits})
    for stage in folders:
        for rate in (250000,500000):
            selected = [r for r in runs if r['stage']==stage and r['symbol_rate']==rate]
            if not selected:
                continue
            matched_frames = [f for f in frames if f['stage']==stage and f['symbol_rate']==rate]
            inside = [f for f in matched_frames if f['data_overlaps_first_period_bin']]
            outside = [f for f in matched_frames if not f['data_overlaps_first_period_bin']]
            good = sum(r['valid_unique_frames'] for r in selected)
            expected = sum(r['expected_frames'] for r in selected)
            bins = [r for r in phases if r['stage']==stage and r['symbol_rate']==rate]
            bin0 = bins[0]
            assert bin0['phase_start_tx_samples']==0
            result = {'stage':stage, 'symbol_rate':rate, 'bursts':len(selected), 'valid_frames':good,
                      'expected_frames':expected, 'loss_pct':100*(expected-good)/expected,
                      'goodput_bps':mean(r['payload_goodput_bps'] for r in selected),
                      'whole_burst_goodput_bps':mean(r['whole_burst_goodput_bps_10ms'] for r in selected),
                      'first_128us_ber_pct':100*bin0['ber'],
                      'rest_of_period_ber_pct':100*sum(r['bit_errors'] for r in bins[1:])/sum(r['bits_compared'] for r in bins[1:]),
                      'overlap_lost':sum(not int(f['crc_and_payload_ok']) for f in inside),
                      'overlap_total':len(inside),
                      'nonoverlap_lost':sum(not int(f['crc_and_payload_ok']) for f in outside),
                      'nonoverlap_total':len(outside)}
            aggregate.append(result)
            print(result)
    write_table(out/'before-after.csv', aggregate)
    write_table(out/'run-summary.csv', runs)
    write_table(out/'frame-outcomes.csv', frames)
    write_table(out/'phase-summary.csv', phases)
    write_table(out/'phase-by-run.csv', phase_by_run)
    (out/'capture-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('schedule','before','recorded','output'):
        cli.add_argument(name, type=Path)
    args=cli.parse_args()
    report(args.schedule,args.before,args.recorded,args.output)
