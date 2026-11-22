"""Replay QPSK A/B captures and fit the residual RF carrier from verified frames."""
import csv
import json
from pathlib import Path
import sys

import numpy as np


def report(root,out):
    rows=[]
    for rate in (250000,500000):
        for condition in ('fresh','biased'):
            path=root/f'qpsk-{rate}-{condition}'
            with (path/'replay'/'data-aided-model.csv').open() as handle:
                results=list(csv.DictReader(handle))
            with (path/'replay'/'ablation.csv').open() as handle:
                replay=list(csv.DictReader(handle))
            leakage=np.array([float(r['raw_leakage_relative_dbc']) for r in results])
            corrected=[r for r in replay if r['mode']=='local_mean_leakage']
            assert len(corrected)==256 and len(leakage)==256
            summary=np.load(path/'symbols.npz')
            modes=[r for r in replay if r['mode']=='baseline']
            tx_log=(path/'tx-result.log').read_text()
            rows.append({'run':path.name,'symbol_rate':rate,'tx_sample_bias':condition,
                         'rf24_calibration':next(l for l in tx_log.splitlines() if l.startswith('TX_CAL ')),
                         'median_carrier_relative_dbc':np.median(leakage),
                         'p10_carrier_relative_dbc':np.percentile(leakage,10),
                         'p90_carrier_relative_dbc':np.percentile(leakage,90),
                         'baseline_decode_valid':sum(int(r['valid']) for r in modes),
                         'tracking_decode_valid':sum(int(r['valid']) for r in corrected),
                         'tracking_data_field_bit_errors':sum(int(r['bit_errors']) for r in corrected),
                         'adc_component_clip_fraction':float(summary['clip']),
                         'detected_frames':len(leakage)})
            print(json.dumps(rows[-1]))
    with out.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


if __name__=='__main__':
    report(Path(sys.argv[1]),Path(sys.argv[2]))
