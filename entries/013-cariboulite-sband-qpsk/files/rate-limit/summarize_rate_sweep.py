"""Build the rate-sweep results, pilot timing checks and SigMF metadata."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np


def write_table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def report(archive, out):
    rows, metadata, spacing, all_frames = [], {}, [], []
    hashes={name:sha for f in ('grid-sha256.txt','later-sha256.txt')
            for sha,name in (line.split() for line in (archive/f).read_text().splitlines())}
    keys=sorted(hashes, key=lambda k:(k.startswith('at4'),k.startswith('long'),int(k.split('/')[0].split('-')[-1]),k))
    for name in keys:
        folder=(archive/name).parent
        run=folder.name
        summary=json.loads((folder/'decoded/summary.json').read_text())
        baud=summary['baud']
        wave_name=f"at4-{baud}" if run.startswith('at4-') else f"qpsk-{baud}"
        if run.startswith('long-'):
            wave_name=run
        build=json.loads((archive/'waveforms'/f'{wave_name}.json').read_text())
        assert build['baud']==baud and build['tx_sample_rate']==summary['tx_sample_rate']
        timing=(folder/'tx-result.log').read_text()
        write=re.search(r'requested=(\d+) accepted=(\d+) partial=(\d+) elapsed=([\d.]+)',timing)
        config=re.search(r'TXDFE=(\S+) FPGA_GAP=(\d+)',timing)
        state=re.search(r'RF_STATE TX=(\d+)/(\d+) IQ_SYNC=(\d+)/(\d+)',timing)
        cal=re.search(r'TX_CAL mode=fresh I=(\d+) Q=(\d+)',timing)
        assert write and config and state and cal
        assert write[1]==write[2] and int(write[3])==0
        strobe=int(run.split('-')[1][1:]) if run.startswith('at4-s') else 12
        rows.append({'run':run,**summary,'nominal_rf_width_hz':baud*1.35,'smi_write_strobe':strobe,
                     'txdfe':config[1],'fpga_gap':int(config[2]),'rf24_i':int(cal[1]),'rf24_q':int(cal[2]),
                     'tx_iq_accepted':int(write[2]),'tx_short_writes':int(write[3]),
                     'tx_write_elapsed_s':float(write[4]),'tx_active_polls':int(state[1]),
                     'tx_poll_count':int(state[2]),'iq_sync_polls':int(state[3]),'iq_sync_poll_count':int(state[4])})
        with (folder/'decoded/detections.csv').open(newline='') as f:
            detections=list(csv.DictReader(f))
        fs=summary['tx_sample_rate']
        assert len(detections)==summary['preambles']
        times=np.array([float(r['pilot_start_s']) for r in detections])
        all_frames.extend({'run':run,**d} for d in detections)
        spacing_row={'run':run,'detected_preambles':len(times),'expected_preambles':summary['expected_frames'],
                     'median_gap_delta_tx_samples':'','p01_gap_delta_tx_samples':'','p99_gap_delta_tx_samples':'',
                     'sum_gap_delta_tx_samples':''}
        if len(times)==summary['expected_frames']:
            diff=(np.diff(times)-2272/baud)*fs
            spacing_row.update({'median_gap_delta_tx_samples':float(np.median(diff)),
                                'p01_gap_delta_tx_samples':float(np.quantile(diff,.01)),
                                'p99_gap_delta_tx_samples':float(np.quantile(diff,.99)),
                                'sum_gap_delta_tx_samples':float(np.sum(diff))})
        spacing.append(spacing_row)
        start=(folder/'capture-start-utc.txt').read_text().strip()
        raw=archive/name
        assert raw.stat().st_size== (400_000_000 if run.startswith('long-') else 120_000_000)
        sg={'global': {'core:datatype':'ci8','core:sample_rate':8_000_000,'core:version':'1.2.0','core:hw':'HackRF One',
                       'core:description':(f'{run}, nominal 2250 MHz conducted QPSK. 30 dB pad, minimum '
                                           f'TX PA, LNA/VGA 32/24 dB, RF amp and bias off. Capture '
                                           f'command UTC {start}. Sample-zero time uncalibrated.')},
            'captures':[{'core:sample_start':0,'core:frequency':2249850000}],'annotations':[]}
        (folder/'receive.sigmf-meta').write_text(json.dumps(sg,indent=2)+'\n')
        metadata[run]={'capture_sha256':hashes[name],'capture_bytes':raw.stat().st_size,
                       'sigmf':sg,'tx_waveform':build}
    assert len(rows)==16
    write_table(out/'rate-results.csv',rows)
    write_table(out/'pilot-timing.csv',spacing)
    write_table(out/'frame-diagnostics.csv',all_frames)
    (out/'capture-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    for r in rows:
        print(r['run'],r['tracked_frames'],r['equalized_frames'],'/',r['expected_frames'],
              round(r['equalized_goodput_bps']/1e6,3),r['tx_write_elapsed_s'])
    print('Long timing',next(r for r in spacing if r['run'].startswith('long-')))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    report(a.archive,a.output)
