"""Audit counts, frozen selection, training/held-out decisions and input preservation."""
import json,csv,hashlib,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'offline-ber';BASE=HERE.parent/'offline-geometry-v3'
sys.path.insert(0,str(OLD))
from diagnostic import frame_reference,score_bits,crc_observation
selection=json.loads((HERE/'selection.json').read_text())
for key in ['frozen_receiver_model','development_hashes']:
 for f,digest in selection[key].items():
    assert hashlib.sha256((HERE/f).read_bytes()).hexdigest()==digest,(key,f)
assert hashlib.sha256((HERE.parent/'offline-start-v2/receiver.py').read_bytes()).hexdigest()==selection['acquisition_sha256']
assert hashlib.sha256((BASE/'receiver.py').read_bytes()).hexdigest()==selection['pair_detector_sha256']
manifest=json.loads((OLD/'manifest.json').read_text());sources={s['name']:s for s in manifest['sources']}
for s in sources.values():
 assert hashlib.sha256((OLD/s['filename']).read_bytes()).hexdigest()==s['npz_sha256']
training=[json.loads(s) for s in (HERE/'training-trials.jsonl').read_text().splitlines()]
expected,_=frame_reference(sources['libre01']['native_hex'],sources['libre01']['rf_sequence'])
for r in training:
 if r['kind']=='noise' or not r['detected']:continue
 bits=np.unpackbits(np.frombuffer(bytes.fromhex(r['decisions_hex']),np.uint8)).astype(np.int8);bits[0]=-1
 assert score_bits(bits,expected)['bit_errors']==r['bit_errors']
 idx=np.arange(68,252)
 assert int(np.sum(bits[idx[expected[idx]==0]]!=0))==r['false_changes']
 assert int(np.sum(bits[idx[expected[idx]==1]]!=1))==r['missed_changes']
 assert (r['sync_errors']==0 and crc_observation(bits))==r['frame_pass']
assert len(training)==364
for r in csv.DictReader((HERE/'training-summary.csv').open()):
 group=[x for x in training if x['version']==r['version'] and (x['kind']==r['point'] or (x['kind']=='noisy' and str(x['ebn0_db'])==r['point']))]
 aligned=[x for x in group if x.get('aligned',False)]
 calculated=dict(trials=len(group),detected=sum(x['detected'] for x in group),
   aligned=len(aligned),frames=sum(x.get('frame_pass',False) for x in group),
   aligned_bits=184*len(aligned),aligned_errors=sum(x['bit_errors'] for x in aligned),
   false_changes=sum(x['false_changes'] for x in aligned),missed_changes=sum(x['missed_changes'] for x in aligned))
 assert all(calculated[k]==int(r[k]) for k in calculated)

rows=[json.loads(s) for s in (HERE/'trials.jsonl').read_text().splitlines()]
sync=np.unpackbits(np.frombuffer(bytes.fromhex('1acffc1d'),np.uint8))
for r in rows:
 if r['capture'] not in sources or not r['detected']:continue
 bits=np.unpackbits(np.frombuffer(bytes.fromhex(r['decisions_hex']),np.uint8)).astype(np.int8);bits[0]=-1
 assert len(bits)==808
 assert int(np.sum(bits[256:288]!=sync))==r['sync_errors']
 assert (r['sync_errors']==0 and crc_observation(bits))==r['frame_pass']
 assert (abs(r['start_sample']-r['true_start_sample'])<=20)==r['aligned_within_half_symbol']

for r in csv.DictReader((HERE/'summary.csv').open()):
 group=[x for x in rows if x['capture']==r['capture'] and ((r['ebn0_db']=='clean' and x['kind']=='clean') or (x['kind']=='noisy' and str(x['ebn0_db'])==r['ebn0_db']))]
 assert len(group)==int(r['trials'])
 for field in ['aligned','frames','scored_bits','bit_errors','misses','wrong_start']:
    values={'aligned':lambda x:x['aligned_within_half_symbol'],
      'frames':lambda x:x.get('frame_pass',False),'scored_bits':lambda x:x['scored_bits'],
      'bit_errors':lambda x:x['bit_errors'] or 0,'misses':lambda x:not x['detected'],
      'wrong_start':lambda x:x['detected'] and not x['aligned_within_half_symbol']}
    assert sum(values[field](x) for x in group)==int(r[field]),field
assert len(rows)==214
model=json.loads((HERE/'model.json').read_text());base_model=json.loads((BASE/'model.json').read_text())
assert {k:v for k,v in model.items() if k!='sequence_window'}==base_model
assert model['sequence_window']==selection['selected_window']
for directory in [BASE,HERE.parent/'offline-start-v2',HERE.parent/'offline-blind']:
 baseline=json.loads((directory/'publication.json').read_text())
 for item in baseline['files']:
    assert hashlib.sha256((directory/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
 if 'figure' in baseline:
    figure=baseline['figure']
    assert hashlib.sha256((directory/figure['path']).read_bytes()).hexdigest()==figure['sha256']
assert all(len(r['input_iq_sha256'])==64 for r in rows)
report=dict(frozen_selection_and_development_hashes_match=True,all_source_npz_hashes_unchanged=True,
    all_v1_v2_v3_published_file_hashes_unchanged=True,training_ledger_rows_recounted=364,
    held_out_ledger_rows=214,all_summary_counts_recounted=True,
    individual_trial_input_hashes_present=True,shared_diagnostic_sha256=hashlib.sha256((OLD/'diagnostic.py').read_bytes()).hexdigest())
(HERE/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
