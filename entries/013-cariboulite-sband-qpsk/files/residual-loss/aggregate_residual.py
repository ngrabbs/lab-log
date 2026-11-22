"""Aggregate QPSK receiver ablations and compare with the archived decoder output."""
import argparse
import csv
import json
from pathlib import Path
from statistics import median


def read_csv(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with path.open('w',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def report(source, original, out):
    run_rows, frame_rows, model_rows, decile_rows, rate_rows = [], [], [], [], []
    for group, tag, rate, payload_seed, order_seed in (
        line.split('\t') for line in (source/'schedule.tsv').read_text().splitlines()
    ):
        cached = source/group/tag
        archive = original/('after' if group=='patched' else 'control')/tag
        original_data = json.loads((archive/'summary.json').read_text())
        original_frames = read_csv(archive/'frames.csv')
        archive_hash = (archive/'receive-sha256.txt').read_text().split()[0]
        stage = ('development' if tag.startswith('r1-') else 'holdout') if group=='patched' else 'old-driver control'
        ident = {'group':group,'split':stage,'run':tag,'symbol_rate':int(rate),
                 'payload_seed':int(payload_seed),'order_seed':int(order_seed)}
        ablation = read_csv(cached/'ablation.csv')
        for mode in dict.fromkeys(r['mode'] for r in ablation):
            selected = [r for r in ablation if r['mode']==mode]
            assert len(selected)==256 and {int(r['position']) for r in selected}==set(range(256))
            valid = sum(int(r['valid']) for r in selected)
            false_crc = sum(int(r['crc_ok']) and not int(r['valid']) for r in selected)
            bit_errors = sum(int(r['bit_errors']) for r in selected)
            assert false_crc==0
            if mode=='baseline':
                assert valid==original_data['valid_unique_frames']
                assert all(int(a['valid'])==int(b['crc_and_payload_ok']) for a,b in zip(selected,original_frames))
            run_rows.append({**ident,'mode':mode,'frames_valid':valid,'frames_total':256,
                             'data_field_bit_errors':bit_errors,'wrong_payload_crc_passes':false_crc,
                             'packet_loss_pct':100*(256-valid)/256,
                             'packet_train_goodput_bps':valid*4096/original_data['scheduled_packet_train_s'],
                             'whole_burst_goodput_bps':valid*4096/(original_data['rf_end_s_10ms']-original_data['rf_start_s_10ms']),
                             'adc_component_clip_fraction':original_data['adc_component_clip_fraction'],
                             'raw_capture_sha256':archive_hash})
        frame_rows.extend({**ident,**r} for r in ablation)
        model_rows.extend({**ident,**r} for r in read_csv(cached/'data-aided-model.csv'))

    for rate in (250000,500000):
        for mode in dict.fromkeys(r['mode'] for r in run_rows):
            selected = [r for r in run_rows if r['group']=='patched' and r['symbol_rate']==rate and r['mode']==mode]
            assert len(selected)==3 and sum(r['split']=='holdout' for r in selected)==2
            valid = sum(r['frames_valid'] for r in selected)
            valid_held = sum(r['frames_valid'] for r in selected if r['split']=='holdout')
            rate_rows.append({'symbol_rate':rate,'mode':mode,'valid_frames':valid,'total_frames':768,
                              'valid_frames_holdout':valid_held,'total_frames_holdout':512,
                              'data_field_bit_errors':sum(r['data_field_bit_errors'] for r in selected),
                              'packet_train_goodput_bps':sum(r['packet_train_goodput_bps'] for r in selected)/3,
                              'whole_burst_goodput_bps':sum(r['whole_burst_goodput_bps'] for r in selected)/3})
            frames = [r for r in frame_rows if r['group']=='patched' and r['symbol_rate']==rate and r['mode']==mode]
            for decile in range(1,11):
                decile_rows.append({'symbol_rate':rate,'mode':mode,'payload_decile':decile,
                                    'data_field_bit_errors':sum(int(r[f'errors_decile_{decile}']) for r in frames),
                                    'data_field_bits_checked':len(frames)*416})
        for passed in (True,False):
            model = [r for r in model_rows if r['group']=='patched' and r['symbol_rate']==rate and bool(int(r['baseline_valid']))==passed]
            metrics = {
                'abs_pilot_cfo_error_hz':median(abs(float(r['pilot_cfo_error_hz'])) for r in model),
                'end_leakage_error_rel':median(float(r['baseline_leakage_error_end']) for r in model),
                'mid_leakage_error_rel':median(float(r['baseline_leakage_error_mid']) for r in model),
                'leakage_dbc':median(float(r['raw_leakage_relative_dbc']) for r in model),
                'abs_signal_minus_leakage_hz':median(abs(float(r['data_aided_signal_hz'])-float(r['data_aided_leakage_hz'])) for r in model),
            }
            print(rate,'pass' if passed else 'fail',len(model),metrics)
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'replay-by-run.csv',run_rows)
    write_csv(out/'replay-by-rate.csv',rate_rows)
    write_csv(out/'frame-ablation.csv',frame_rows)
    write_csv(out/'data-aided-leakage-fit.csv',model_rows)
    write_csv(out/'bit-errors-by-decile.csv',decile_rows)
    for r in rate_rows:
        print(r)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('source','original','out'):
        parser.add_argument(arg,type=Path)
    args=parser.parse_args()
    report(args.source,args.original,args.out)
