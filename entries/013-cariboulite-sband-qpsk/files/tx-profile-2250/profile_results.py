"""Summarize saved-profile RX results and write SigMF sidecars."""
import argparse
import csv
import json
from pathlib import Path
import re
from statistics import median


def summarize(plan, captures, out):
    with plan.open(newline='') as f:
        trials=list(csv.DictReader(f,delimiter='\t'))
    hashes={name:digest for digest,name in (line.split() for line in (captures/'capture-sha256.txt').read_text().splitlines())}
    rows,manifest,fits=[],[],[]
    for trial in trials:
        run=trial['run']
        rate=int(trial['rate'])
        capture=captures/run
        tx=(capture/'tx-result.log').read_text()
        profile=re.search(r'TX_PROFILE 2250 MHz fresh RF24 bias_i=(\S+) bias_q=(\S+) input_samples=(\d+) pad_samples=(\d+)',tx)
        cal=re.search(r'TX_CAL mode=(\S+) I=(\d+) Q=(\d+) startup_I=(\d+) startup_Q=(\d+)',tx)
        write=re.search(r'requested=(\d+) accepted=(\d+) partial=(\d+)',tx)
        assert profile and cal and write
        iq_count=int(profile[3])+int(profile[4])
        assert profile[1]=='128' and profile[2]=='-4280' and cal[1]=='fresh'
        assert int(write[1])==int(write[2])==iq_count and write[3]=='0'
        ablations=read_table(capture/'replay/ablation.csv')
        models=read_table(capture/'replay/data-aided-model.csv')
        assert len(models)==256
        tracked=[r for r in ablations if r['mode']=='local_mean_leakage']
        baseline=[r for r in ablations if r['mode']=='baseline']
        assert len(tracked)==len(baseline)==len(models)
        model_median=median(float(r['raw_leakage_relative_dbc']) for r in models)
        for model,tracked_frame in zip(models,tracked):
            assert model['position']==tracked_frame['position']
            fits.append({'run':run,'symbol_rate':rate,**model,'tracking_crc_valid':tracked_frame['valid'],
                         'tracking_bit_errors':tracked_frame['bit_errors']})
        metrics=json.loads((capture/'extract-metrics.json').read_text())
        assert float(metrics['clip'])==0 and int(metrics['cfo'])==22100
        recovery=sum(int(r['valid']) for r in tracked)
        row={**trial,'rf24_i':int(cal[2]),'rf24_q':int(cal[3]),'startup_i':int(cal[4]),'startup_q':int(cal[5]),
             'iq_bias_i':int(profile[1]),'iq_bias_q':int(profile[2]),'tx_iq_samples':iq_count,'tx_partial_writes':int(write[3]),
             'frames_scheduled':256,'preambles_found':len(models),'frames_valid':recovery,
             'original_decoder_valid_with_hint':sum(int(r['valid']) for r in baseline),
             'tracked_data_field_errors':sum(int(r['bit_errors']) for r in tracked),
             'payload_goodput_bps':recovery*4096*rate/(256*2272),'adc_component_clip_fraction':metrics['clip'],
             'median_carrier_dbc':model_median}
        rows.append(row)
        data=capture/'receive.sigmf-data'
        assert data.stat().st_size==120_000_000
        capture_time=(capture/'capture-start-utc.txt').read_text().strip()
        sg={'global':{'core:datatype':'ci8','core:sample_rate':8_000_000,'core:version':'1.2.0','core:hw':'HackRF One',
                      'core:description':(f'{run} post-reboot 2250 MHz TX profile. Pad 30 dB and LNA/VGA 32/24 dB. '
                                          f'Capture command UTC {capture_time}, sample-zero time uncalibrated.')},
            'captures':[{'core:sample_start':0,'core:frequency':2249500000}],'annotations':[]}
        (capture/'receive.sigmf-meta').write_text(json.dumps(sg,indent=2)+'\n')
        manifest.append({'run':run,'sha256':hashes[f'{run}/receive.sigmf-data'],'size_bytes':data.stat().st_size,
                         'capture_command_start_utc':capture_time,'sigmf':sg})
        print(json.dumps(row))
    write_table(out/'profile-runs.csv',rows)
    write_table(out/'profile-frame-fits.csv',fits)
    (out/'capture-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


def read_table(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def write_table(path, rows):
    with path.open('w',newline='') as handle:
        csv_out=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n')
        csv_out.writeheader()
        csv_out.writerows(rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','captures','output'):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    summarize(args.plan,args.captures,args.output)
