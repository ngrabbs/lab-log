"""Freeze v2 from training-only acquisition criteria before held-out execution."""
import json,csv,hashlib,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
rows=list(csv.DictReader((HERE/'training-summary.csv').open()))
v1=[r for r in rows if r['version']=='v1' and r['point'] in ['8','12']]
v2=[r for r in rows if r['version']=='v2' and r['point'] in ['8','12']]
old=sum(int(r['aligned']) for r in v1);new=sum(int(r['aligned']) for r in v2)
clean=next(r for r in rows if r['version']=='v2' and r['point']=='clean')
noise=next(r for r in rows if r['version']=='v2' and r['point']=='noise')
selected=new>old and new==60 and int(clean['frames'])==1 and int(noise['detected'])==0
assert selected,'Training acquisition criteria not met; do not run held-out tests.'
selection=dict(selected=selected,selection_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 criterion='Improve training start acquisition, acquire all 60 noisy cases and clean frame, and emit no candidate in 30 noise-only windows.',
 training_iq='libre01 only',training_noisy_trials=60,v1_aligned=old,v2_aligned=new,
 training_seeds=[44001,44002,44003],training_noise_control_seed_start=850000,
 no_held_out_iq_used_in_training=True,
 not_selected_for='CRC/frame success or scored BER; training frame counts are mixed.',
 frozen_receiver_model={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['model.json','receiver.py']},
 development_hashes={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['train.py','training-source.json','training-trials.jsonl','training-summary.csv','test_receiver.py','tests.txt','run.py']},
 held_out_plan='Same 180 paired noisy cases, 3 clean cases and 30 noise controls as v1; no receiver retuning after inspection.',
 tested_capture_history='Retrospective reused captures; prior v1 outcomes were known before this work.')
(HERE/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
print(json.dumps(selection,indent=2))
