"""Behavioral tests for BER accounting, synchronization isolation and noise scaling."""
import unittest,math
import numpy as np
import diagnostic as d

class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.native='0901c011001f0101000502010000000000000000f8c21adc05d3250100060301000000000a35'
        self.bits,self.states=d.frame_reference(self.native,21)
        self.start=8000;self.cfo=-3500.
        self.source=dict(native_hex=self.native,rf_sequence=21,preamble_start_symbol=200,timing_sample=0,refined_cfo_hz=self.cfo)
        clean=np.zeros(4*d.RATE,complex)
        clean[self.start:self.start+len(self.bits)*40]=np.repeat(1-2*self.states.astype(int),40)/math.sqrt(40)
        self.iq=clean*np.exp(2j*np.pi*self.cfo*np.arange(len(clean))/d.RATE)
        self.ref=d.freeze(self.iq,self.source)

    def test_clean_frame(self):
        r=d.scheduled_diagnostic(self.iq,self.ref)
        self.assertEqual(r['bit_errors'],0);self.assertEqual(r['scored_bits'],184)
        self.assertTrue(r['sync_exact']);self.assertTrue(r['scheduled_frame_pass'])

    def test_template_estimator_corrects_known_offset_without_payload_truth(self):
        r=d.scheduled_diagnostic(self.iq,self.ref,'template')
        self.assertLess(abs(r['carrier_estimate_hz']-self.cfo),.5)
        self.assertEqual(r['bit_errors'],0)
        ref=dict(self.ref);ref['expected_bits']=self.bits.copy();ref['expected_bits'][68:]=1-ref['expected_bits'][68:]
        self.assertEqual(d.template_cfo(self.iq,self.ref),d.template_cfo(self.iq,ref))

    def test_failed_crc_does_not_discard_decisions(self):
        x=self.iq.copy();a=self.start+350*40;x[a:a+40]*=-1
        r=d.scheduled_diagnostic(x,self.ref)
        self.assertFalse(r['outer_crc32_pass']);self.assertEqual(r['scored_bits'],184)
        self.assertGreater(r['replay_reference_body_errors'],0);self.assertEqual(len(r['bits']),808)

    def test_bad_header_cannot_shorten_the_ber_window(self):
        x=self.iq.copy();a=self.start+288*40;x[a:a+40]*=-1
        r=d.scheduled_diagnostic(x,self.ref)
        self.assertFalse(r['outer_crc32_pass']);self.assertEqual(r['scored_bits'],184)
        self.assertEqual(len(r['bits']),808)

    def test_preamble_errors_are_retained_even_with_valid_body_crc(self):
        x=self.iq.copy();a=self.start+100*40;x[a:a+40]*=-1
        r=d.scheduled_diagnostic(x,self.ref)
        self.assertEqual(r['bit_errors'],2);self.assertEqual(r['error_positions'],[100,101])
        self.assertEqual(r['scored_bits'],184)

    def test_sync_failure_is_separate_from_ber(self):
        x=self.iq.copy();a=self.start+260*40;x[a:a+40]*=-1
        r=d.scheduled_diagnostic(x,self.ref)
        self.assertFalse(r['sync_exact']);self.assertFalse(r['scheduled_frame_pass'])
        self.assertEqual(r['scored_bits'],184)

    def test_truth_outside_training_cannot_choose_timing(self):
        corrected=self.iq*np.exp(-2j*np.pi*self.cfo*np.arange(len(self.iq))/d.RATE)
        b=self.bits.copy();b[68:]=1-b[68:]
        _,a,metric=d.choose_training_timing(corrected,8000,self.bits,808)
        _,c,other=d.choose_training_timing(corrected,8000,b,808)
        self.assertEqual(a,c);self.assertEqual(metric,other)

    def test_invalid_and_missing_samples_are_erasures(self):
        x=self.iq.copy();x[4]=np.nan
        self.assertFalse(d.scheduled_diagnostic(x,self.ref)['scorable'])
        self.assertFalse(d.scheduled_diagnostic(self.iq[:100],self.ref)['scorable'])
        self.assertFalse(d.score_bits(np.array([0,1]),self.bits)['scorable'])
        self.assertEqual(d.cluster_interval([],184)[0],None)

    def test_frozen_cli_rejects_nan_as_erasure(self):
        import tempfile,json,subprocess,sys
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);np.savez(p/'clean.npz',iq=self.iq)
            bad=self.iq.copy();bad[0]=np.nan;np.save(p/'bad.npy',bad)
            (p/'manifest.json').write_text(json.dumps(dict(sources=[dict(name='test',filename='clean.npz',**self.source)])))
            r=subprocess.run([sys.executable,str(Path(d.__file__)),'--manifest',str(p/'manifest.json'),'--capture','test','--iq',str(p/'bad.npy'),'--mode','frozen'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            result=json.loads(r.stdout);self.assertFalse(result['scorable']);self.assertEqual(result['scored_bits'],0)

    def test_waveform_sufficient_statistics_and_noise_energy(self):
        rng=np.random.default_rng(101);ns=8;n=20000;n0=.7
        b=rng.integers(0,2,n);wave=np.repeat(2*b-1,ns)/math.sqrt(ns)
        noise=math.sqrt(n0/2)*(rng.normal(size=n*ns)+1j*rng.normal(size=n*ns))
        actual=d.integrate(wave+noise,0,n,ns)
        projected=noise.reshape(n,ns).sum(axis=1)/math.sqrt(ns)
        np.testing.assert_allclose(actual,(2*b-1)+projected,atol=2e-15)
        self.assertLess(abs(np.mean(abs(projected)**2)/n0-1),.03)
        self.assertAlmostEqual(np.sum(abs(wave[:ns])**2),1.)

if __name__=='__main__':unittest.main()
