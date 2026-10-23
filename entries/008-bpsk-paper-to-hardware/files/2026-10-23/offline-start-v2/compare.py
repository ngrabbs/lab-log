"""Paired retrospective comparison, run only after the receiver is frozen/tested."""
import json,csv,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'offline-blind'
old=[json.loads(x) for x in (BASE/'trials.jsonl').read_text().splitlines()]
new=[json.loads(x) for x in (HERE/'trials.jsonl').read_text().splitlines()]
def key(r):return (r['capture'],r['kind'],r.get('ebn0_db'),r.get('seed'),r.get('trial'))
a={key(r):r for r in old};b={key(r):r for r in new};assert a.keys()==b.keys()
for k,r in a.items():
    s=b[k]
    for field in ['injected_delay_samples','injected_cfo_hz','injected_phase_rad','gain','true_start_sample','true_cfo_hz']:
        assert r.get(field)==s.get(field),(k,field)
rows=[]
for name in ['libre02','pluto00','pluto20','ALL']:
 for eb in [8,12,'ALL']:
    keys=[k for k in a if k[1]=='noisy' and (name=='ALL' or k[0]==name) and (eb=='ALL' or k[2]==eb)]
    row=dict(capture=name,ebn0_db=eb,trials=len(keys))
    for outcome,field in [('start','aligned_within_half_symbol'),('frame','frame_pass')]:
        pairs=[(bool(a[k].get(field,False)),bool(b[k].get(field,False))) for k in keys]
        row.update({outcome+'_v1_pass':sum(x for x,y in pairs),outcome+'_v2_pass':sum(y for x,y in pairs),
           outcome+'_recovered':sum(not x and y for x,y in pairs),outcome+'_regressed':sum(x and not y for x,y in pairs),
           outcome+'_both_fail':sum(not x and not y for x,y in pairs)})
    rows.append(row)
with (HERE/'paired-summary.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def generation_kernel(path):
    text=path.read_text()
    return text[text.index("        for eb in model['ebn0_db']:"):text.index('    groups=[]')]
assert generation_kernel(HERE/'run.py')==generation_kernel(BASE/'run.py')
report=dict(noisy_input_generation_kernel_byte_identical=True,paired_trial_keys_match=True,all_recorded_nuisance_and_truth_values_match=True,
    baseline_ledger_sha256=hashlib.sha256((BASE/'trials.jsonl').read_bytes()).hexdigest(),
    baseline_receiver_sha256=hashlib.sha256((BASE/'receiver.py').read_bytes()).hexdigest(),
    model_identical_to_baseline=(HERE/'model.json').read_bytes()==(BASE/'model.json').read_bytes(),
    noise_generation='Identical source inputs, RNG streams, draws and transformations; v2 additionally logs exact input IQ hashes.',
    total_noisy_trials=180)
(HERE/'paired-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(rows[-1],indent=2))
