import unittest,numpy as np
from model_test import *
class SyntheticTests(unittest.TestCase):
 def test_truth_frame_and_crc(self):
    for pattern in PATTERNS:
       meta,truth,z,h,gain=make_case(pattern,'static','clean',99101,'detector',0)
       np.testing.assert_array_equal(truth[PAYLOAD],payload(pattern,np.random.default_rng(1))) if pattern!='random_iid' else None
       self.assertEqual(len(truth),808);self.assertTrue(crc_observation(truth))
       for name,bits in detectors(z,h,gain).items():
          self.assertEqual(metrics(bits,truth)['payload_errors'],0,(pattern,name))
 def test_integration_factor(self):
    rng=np.random.default_rng(1);p,_=phase('residual010',rng,phi0=.3)
    h=np.exp(1j*p).reshape(808,40).mean(axis=1)
    factor=np.mean(np.exp(2j*np.pi*.1*np.arange(40)/40))
    np.testing.assert_allclose(h,np.exp(1j*(.3+2*np.pi*.1*np.arange(808)))*factor,atol=2e-13)
 def test_noise_projection_unit_energy(self):
    rng=np.random.default_rng(2);w=(rng.normal(size=(20000,40))+1j*rng.normal(size=(20000,40)))/np.sqrt(2)
    z=w.sum(axis=1)/np.sqrt(40)
    self.assertLess(abs(np.mean(abs(z)**2)-1),.025)
 def test_noisy_case_reproducibility(self):
    a=make_case('random_iid','walk3',8,99101,'full',1)
    b=make_case('random_iid','walk3',8,99101,'full',1)
    self.assertEqual(a[0],b[0]);np.testing.assert_array_equal(a[2],b[2])
 def test_erasure_not_correct_payload(self):
    r=metrics(None,np.zeros(808),False);self.assertEqual(r['scored_bits'],0);self.assertIsNone(r['payload_errors']);self.assertFalse(r['packet_pass'])
 def test_common_geometry_scale_does_not_change_detector(self):
    rng=np.random.default_rng(8031);z=rng.normal(size=808)+1j*rng.normal(size=808)
    raw=np.array([complex(*v) for v in MODEL['centers']])
    np.testing.assert_array_equal(v4.pair.pair_glrt(z,raw),v4.pair.pair_glrt(z,MU))
    np.testing.assert_array_equal(v4.sequence_glrt(z,raw,3)[0],v4.sequence_glrt(z,MU,3)[0])
 def test_frozen_parameters(self):self.assertEqual(len(freeze_check()),4)
if __name__=='__main__':unittest.main()
