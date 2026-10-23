"""Training-only preparation; run before inspecting held-out receiver outcomes."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'offline-ber'
sys.path.insert(0,str(OLD))
from diagnostic import freeze
manifest=json.loads((OLD/'manifest.json').read_text())
s=next(s for s in manifest['sources'] if s['name']=='libre01')
x=np.load(OLD/s['filename'])['iq'];r=freeze(x,s)
mu=np.array([complex(*v) for v in r['centers']]);mu=mu/mu[0]
model=dict(training_capture='libre01',training_npz_sha256=s['npz_sha256'],
    centers=[[float(v.real),float(v.imag)] for v in mu],threshold=.04,
    rate_hz=48000,sps=40,cfo_search_hz=[-12000,12000],
    acquisition_symbols='0..63 and 256..287 (known sync)',score_symbols='68..251',
    threshold_rationale='Fixed normalized correlation threshold, checked on training only.',
    test_captures=['libre02','pluto00','pluto20'],
    noise_seeds=[73191,73192,73193],trials_per_seed=10,ebn0_db=[8,12],
    limits='Retrospective capture holdout: recordings were examined in prior work, not prospective unseen RF data.')
(HERE/'model.json').write_text(json.dumps(model,indent=2)+'\n')
print(json.dumps(model,indent=2))
