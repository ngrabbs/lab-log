"""Freeze one geometry-aware detector from libre01 results before held-out use."""
import json,csv,hashlib,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'offline-start-v2'
rows=list(csv.DictReader((HERE/'training-summary.csv').open()))
def row(v,p):return next(r for r in rows if r['version']==v and r['point']==str(p))
a=[row('v2',p) for p in [8,12]];b=[row('v3',p) for p in [8,12]]
selected=(int(b[0]['aligned_errors'])<int(a[0]['aligned_errors']) and
 sum(int(r['aligned_errors']) for r in b)<sum(int(r['aligned_errors']) for r in a) and
 all(x['aligned']==y['aligned'] for x,y in zip(a,b)) and
 int(row('v3','clean')['frames'])==1 and int(row('v3','noise')['detected'])==0)
assert selected,'Training BER criteria not met; do not run held-out evaluation.'
ledger=[json.loads(x) for x in (HERE/'training-trials.jsonl').read_text().splitlines()]
for i in range(0,len(ledger),2):
 old,new=ledger[i:i+2]
 for field in ['detected','start_sample','cfo_hz','metric','coarse_metric','block_metrics']:
    assert old.get(field)==new.get(field),field
 if old['detected']:assert old['decisions_hex']==new['baseline_decisions_hex']
selection=dict(selected=selected,selection_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 criterion='Reduce training known-preamble errors at 8 dB and combined 8/12 dB with identical acquisition; retain clean frame and no training noise candidates.',
 training_iq='libre01 only',training_noise_seeds=[55001,55002,55003],noise_control_seed_start=860000,
 training_noisy_trials=60,detector_candidates_evaluated=1,
 selected_detector='Pairwise complex-scale GLRT over learned 00/01/10/11 templates; XOR of selected states.',
 v2_training_errors=[int(x['aligned_errors']) for x in a],v3_training_errors=[int(x['aligned_errors']) for x in b],
 not_selected_for='Frame CRC success or noisy body-reference error counts.',
 acquisition_sha256=hashlib.sha256((BASE/'receiver.py').read_bytes()).hexdigest(),
 frozen_receiver_model={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['model.json','receiver.py']},
 development_hashes={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['train.py','training-source.json','training-trials.jsonl','training-summary.csv','test_receiver.py','tests.txt','run.py']},
 held_out_plan='Same 180 noisy cases, 3 clean cases, 30 noise controls and one training check as v2; exact IQ hashes and acquisition outputs must match; no held-out retuning.',
 scope='Retrospective reused RF recordings. Earlier held-out v2 outcomes were already known.')
(HERE/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
print(json.dumps(selection,indent=2))
