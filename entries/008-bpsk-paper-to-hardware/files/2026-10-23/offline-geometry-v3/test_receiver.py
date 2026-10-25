import unittest,json,sys,inspect
from pathlib import Path
import numpy as np
from receiver import acquire,pair_glrt,acquisition
correlation_search=acquisition.correlation_search
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'offline-ber'))
from diagnostic import frame_reference,crc_observation
class ReceiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model=json.loads((HERE/'model.json').read_text())
    def signal(self,start,freq,broken=False):
        bits,states=frame_reference('00'*38,123)
        if broken:
            bits[350]^=1;states=np.cumsum(bits)%2
        mu=np.array([complex(*v) for v in self.model['centers']])
        x=np.zeros(192000,dtype=complex)
        x[start:start+len(bits)*40]=np.repeat(mu[states],40)
        return x*np.exp(1j*(.87+2*np.pi*freq*np.arange(len(x))/48000)),bits
    def test_api_has_no_truth_inputs(self):
        self.assertEqual(list(inspect.signature(acquire).parameters),['iq','model'])
        for key in ['start_sample','cfo_hz','native_hex','rf_sequence','test_metadata']:
            self.assertNotIn(key,self.model)
    def test_invalid_input_erasure(self):
        for x in [np.zeros(10),np.full(40000,np.nan)]:self.assertFalse(acquire(x,self.model)['detected'])
    def test_unknown_delay_frequency_gain_phase(self):
        for start,freq in [(23017,-9100.3),(123429,8123.7)]:
            x,bits=self.signal(start,freq)
            r=acquire(2.3*x,self.model)
            self.assertTrue(r['detected']);self.assertLessEqual(abs(r['start_sample']-start),1)
            self.assertLess(abs(r['cfo_hz']-freq),1)
            np.testing.assert_array_equal(r['bits'][1:680],bits[1:680])
    def test_failed_crc_retains_decisions(self):
        x,_=self.signal(61011,-4400.2,True);r=acquire(x,self.model)
        self.assertTrue(r['detected']);self.assertEqual(r['sync_errors'],0)
        self.assertFalse(crc_observation(r['bits']));self.assertEqual(len(r['bits']),808)
    def test_start_survives_gap_phase_error(self):
        x,_=self.signal(61011,-4400.2)
        search,_=correlation_search(x,self.model)
        # A 2.5 Hz CFO residual rotates across the gap without being truth
        # supplied to acquire(). This isolates the revised ranking behavior.
        score,start,blocks=search(-4397.7)
        self.assertLessEqual(abs(start-61011),1)
        self.assertGreater(min(blocks),.9)
        self.assertGreater(score,.9)
    def test_zero_input_is_rejected(self):
        self.assertFalse(acquire(np.zeros(192000),self.model)['detected'])
class GeometryTests(unittest.TestCase):
    def test_all_state_pairs_unknown_gain_phase(self):
        mu=np.array([1,np.exp(1j*np.deg2rad(135))])
        for previous,current in [(0,0),(0,1),(1,0),(1,1)]:
            pair=(.3-.8j)*mu[[previous,current]]
            self.assertEqual(pair_glrt(pair,mu).tolist(),[-1,previous^current])
    def test_noisy_change_inside_ninety_degrees(self):
        mu=np.array([1,np.exp(1j*np.deg2rad(135))])
        for angle in [80,-80]:
            pair=np.array([1,np.exp(1j*np.deg2rad(angle))])
            self.assertGreater(np.real(pair[1]*pair[0].conjugate()),0)
            self.assertEqual(pair_glrt(pair,mu)[1],1)
    def test_antipodal_limit_matches_old_detector(self):
        rng=np.random.default_rng(92731)
        z=rng.normal(size=1000)+1j*rng.normal(size=1000)
        old=(np.real(z[1:]*z[:-1].conj())<0).astype(np.int8)
        np.testing.assert_array_equal(pair_glrt(z,np.array([1,-1]))[1:],old)
    def test_invalid_geometry_is_rejected(self):
        for mu in [np.array([0,0]),np.array([1,np.nan])]:
            with self.assertRaises(ValueError):pair_glrt(np.ones(4),mu)
if __name__=='__main__':unittest.main()
