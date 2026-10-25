import unittest,json
from pathlib import Path
import numpy as np
import receiver as r
from train import synthetic
M=json.loads((Path(__file__).parent/'model.json').read_text())
class ReceiverTests(unittest.TestCase):
 def test_empty_zero_nonfinite(self):
    for x in [np.zeros(192000),np.array([]),np.full(40000,np.nan)]:self.assertFalse(r.acquire(x,M)['detected'])
 def test_frequency_phase_and_no_payload_forcing(self):
    rng=np.random.default_rng(952001);mu=r.centers(M);states=rng.integers(0,2,808);states[:64]=r.preamble_states()[:64]
    expected=states[1:]^states[:-1]
    for f in [-144,0,144]:
      z=2.3*mu[states]*np.exp(1j*(1.7+2*np.pi*f*np.arange(808)/1200))
      bits,_=r.detect_symbols(z,M,.04);self.assertTrue(np.array_equal(bits[1:],expected));self.assertEqual(bits[0],-1)
 def test_tracking_improves_ramp_and_reports_frequency(self):
    rng=np.random.default_rng(952002);states=rng.integers(0,2,808);states[:64]=r.preamble_states()[:64];n=np.arange(808);t=n/1200
    z=r.centers(M)[states]*np.exp(1j*(.7+2*np.pi*20*t+np.pi*140*t*t))
    tracked,info=r.track_symbols(z,M,.1)
    self.assertGreater(info['ending_residual_hz'],info['residual_cfo_hz']+60)
    self.assertLess(np.std(np.angle(tracked[200:]/r.centers(M)[states[200:]])),.5)
 def test_acquisition_unknown_start_frequency_ramp(self):
    for profile in ['ramp140','walk15']:
      x,truth,start=synthetic(0,profile,12,912,True);res=r.acquire(x,M)
      self.assertTrue(res['detected']);self.assertLessEqual(abs(res['start_sample']-start),20)
 def test_scaled_input(self):
    x,truth,start=synthetic(1,'static',12,913,True);a=r.acquire(x,M);b=r.acquire(.3*x*np.exp(.8j),M)
    self.assertEqual(a['start_sample'],b['start_sample']);self.assertTrue(np.array_equal(a['bits'],b['bits']))
if __name__=='__main__':unittest.main()
