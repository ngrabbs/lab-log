"""Select window using libre01 only; freeze before any held-out sequence run."""
import json,csv,hashlib,datetime,argparse
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'offline-geometry-v3'
p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');args=p.parse_args()
rows=list(csv.DictReader((HERE/'training-summary.csv').open()))
def row(v,p):return next(r for r in rows if r['version']==v and r['point']==str(p))
base=[row('v3',p) for p in [8,12]];candidates=[]
for length in [3,5,7]:
    records=[row(f'L{length}',p) for p in [8,12]]
    valid=(all(int(a['aligned_errors'])<=int(b['aligned_errors']) for a,b in zip(records,base)) and
           int(records[0]['false_changes'])<int(base[0]['false_changes']) and
           all(a['aligned']==b['aligned'] for a,b in zip(records,base)) and
           int(row(f'L{length}','clean')['frames'])==1 and int(row(f'L{length}','noise')['detected'])==0)
    if valid:candidates.append((sum(int(r['false_changes']) for r in records),sum(int(r['aligned_errors']) for r in records),length))
assert candidates,'No window meets training-only false-transition/BER criteria.'
selected=min(candidates)[2]
base_model=json.loads((BASE/'model.json').read_text());model={**base_model,'sequence_window':selected}
if args.prepare:
    (HERE/'model.json').write_text(json.dumps(model,indent=2)+'\n');print('Selected training window',selected);raise SystemExit
assert json.loads((HERE/'model.json').read_text())==model
assert 'OK' in (HERE/'tests.txt').read_text() and 'FAILED' not in (HERE/'tests.txt').read_text()
ledger=[json.loads(x) for x in (HERE/'training-trials.jsonl').read_text().splitlines()]
for i in range(0,len(ledger),4):
    for r in ledger[i+1:i+4]:
        for field in ['detected','start_sample','cfo_hz','metric','aligned']:
            assert r.get(field)==ledger[i].get(field),field
selection=dict(selected=True,selection_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 criterion='At both points no more training preamble errors than v3; fewer 8 dB false changes; identical acquisition; retain clean frame and zero training-noise candidates. Among eligible windows minimize total false changes, then total errors, then window length.',
 training_iq='libre01 only',training_noise_seeds=[66001,66002,66003],noise_control_seed_start=870000,
 training_noisy_trials=60,candidate_windows=[3,5,7],selected_window=selected,eligible_rank_tuples=candidates,
 selected_detector='Viterbi maximization of summed overlapping-window complex-scale GLRT scores. No transition penalty, known-bit constraints or payload prior.',
 not_selected_for='CRC/frame success or body-reference errors; only clean frame required.',
 acquisition_sha256=hashlib.sha256((HERE.parent/'offline-start-v2/receiver.py').read_bytes()).hexdigest(),
 pair_detector_sha256=hashlib.sha256((BASE/'receiver.py').read_bytes()).hexdigest(),
 frozen_receiver_model={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['model.json','receiver.py']},
 development_hashes={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['train.py','training-source.json','training-trials.jsonl','training-summary.csv','test_receiver.py','tests.txt','run.py']},
 held_out_plan='Only selected window evaluated on same 180 noisy cases, 3 clean cases, 30 controls and one training clean check; no held-out retuning.',
 scope='Retrospective reused RF recordings. Prior v3 results were known. Train/evaluate sequence decisions without body truth or forced preamble/sync bits.')
(HERE/'selection.json').write_text(json.dumps(selection,indent=2)+'\n');print(json.dumps(selection,indent=2))
