import unittest,json
from pathlib import Path
import numpy as np
import receiver as r
M=json.loads((Path(__file__).parent/'model.json').read_text())
class GatedTests(unittest.TestCase):
 def case(self,ramp=0.,noise=0.):
    rng=np.random.default_rng(1080001);states=rng.integers(0,2,808);states[:288]=r.preamble_states();t=np.arange(808)/1200
    z=1.7*r.centers(M)[states]*np.exp(1j*(.8+2*np.pi*33*t+np.pi*ramp*t*t))
    z+=noise*(rng.normal(size=808)+1j*rng.normal(size=808))
    return z,states
 def test_gate_off_exact_preamble_only(self):
    z,_=self.case(0,.3);model=dict(M,gate_drift_score=1e300)
    bits,info=r.detect_symbols(z,model);base=r.v5.detect_symbols(z,model,0.)[0]
    self.assertFalse(info['tracking_enabled']);self.assertEqual(info['accepted_updates'],0);self.assertTrue(np.array_equal(bits,base))
 def test_clean_static_gate_off(self):
    z,states=self.case();bits,info=r.detect_symbols(z,M)
    self.assertFalse(info['tracking_enabled']);self.assertTrue(np.array_equal(bits[1:],states[1:]^states[:-1]));self.assertEqual(bits[0],-1)
 def test_ramp_enables_tracking_without_forced_bits(self):
    z,states=self.case(80);bits,info=r.detect_symbols(z,dict(M,gate_drift_score=3,gate_min_drift_hz_s=20,gate_decision_gap=0))
    self.assertTrue(info['tracking_enabled']);self.assertEqual(info['accepted_updates'],744)
    self.assertGreater(info['ending_residual_hz'],info['residual_cfo_hz']+30)
    self.assertTrue(np.array_equal(bits[1:],states[1:]^states[:-1]))
 def test_rejected_updates_free_run(self):
    z,_=self.case(80,.2);model=dict(M,gate_drift_score=0,gate_min_drift_hz_s=0,gate_decision_gap=1e300)
    bits,info=r.detect_symbols(z,model);base=r.v5.detect_symbols(z,model,0.)[0]
    self.assertTrue(info['tracking_enabled']);self.assertEqual(info['accepted_updates'],0)
    self.assertAlmostEqual(info['ending_residual_hz'],info['residual_cfo_hz']);self.assertTrue(np.array_equal(bits,base))
 def test_gain_phase_invariance(self):
    z,_=self.case(80,.2);a,ia=r.detect_symbols(z,M);b,ib=r.detect_symbols(.4*z*np.exp(.7j),M)
    self.assertTrue(np.array_equal(a,b));self.assertEqual(ia['tracking_enabled'],ib['tracking_enabled']);self.assertAlmostEqual(ia['drift_score'],ib['drift_score'],places=7)
 def test_invalid_input_and_zero_acquisition(self):
    for x in [np.array([]),np.full(808,np.nan)]:
      with self.assertRaises(ValueError):r.detect_symbols(x,M)
    self.assertFalse(r.acquire(np.zeros(192000),M)['detected'])
 def test_decision_gate_reduces_updates(self):
    z,_=self.case(80,.5);model=dict(M,gate_drift_score=0,gate_min_drift_hz_s=0)
    _,a=r.detect_symbols(z,dict(model,gate_decision_gap=0));_,b=r.detect_symbols(z,dict(model,gate_decision_gap=8))
    self.assertEqual(a['accepted_updates'],744);self.assertLess(b['accepted_updates'],744);self.assertGreater(b['accepted_updates'],0)
if __name__=='__main__':unittest.main()
