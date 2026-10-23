# Offline BPSK comparison — October 23, 2026

This is a digital replay experiment using four previously saved RF captures and
independently generated ideal signals. **No new RF transmission, firmware update,
radio configuration or live-decoder change is part of this experiment.**

The result is a connection to the paper: ideal coherent and differential
references reproduce their theory, while the current differential detector on
the recorded waveform has an additional noise penalty. A separate scheduled
synchronization pilot tests the paper's known-preamble idea.

## What was run

All sweeps use `-4, -2, 0, 2, 4, 6, 8, 10, 12 dB` and three independent RNG
streams, seeded `271828`, `314159`, `161803` through NumPy `SeedSequence`.

| Experiment | Fixed budget per point | Reference / purpose |
| --- | --- | --- |
| Frozen CFO/timing waveform comparison | 6,000 noise trials × 184 scored bits = **1,104,000 bits** per curve | Four captures, ideal direct coherent BPSK, ideal DBPSK, and a 135° model |
| Paper compensation reproduction | 18,000 packets × 64 data bits = **1,152,000 bits** per curve | Ns=8, normalized CFO=0.10, PN preambles 16/64, one phase correction |
| Paper integration-loss check | **1,104,000 bits** at each of four offsets | 8 dB, residual normalized offsets 0/0.1/0.25/0.5, symbol-center oracle |
| Scheduled receiver pilot | 150 trials × 184 bits = **27,600 bits** per point/method/capture | LibreSDR 2 and Pluto 20 dB; squared-IQ versus learned-template CFO |

The MATLAB driver inside the submitted archive is byte-identical to the reviewed
`matlab_submission/main.m`. The Python implementation here reproduces its
**equations and algorithms**, not the exact MATLAB random sequence or adaptive
stopping rule. A scalar frequency estimator extracted from the supplied
`python/comms.py` matched the vector implementation exactly on 62 noisy,
positive/negative-offset cases. Rayleigh fading and the paper's full packet-length
sweep were not rerun in this AWGN comparison.

## Ground truth and denominator

The transmitter specifies a 256-bit preamble of 32 bytes of `0x55`. That provides
independent truth without assuming any reconstructed heartbeat payload is the
original saved TX buffer.

- Logical symbols **4–63** train the diagnostic timing metric and state means.
- Logical bits **68–251**, inclusive, are the **184 scored known preamble bits**.
  Four symbols separate training and scoring. The last four preamble symbols and
  the unobserved first differential predecessor are excluded.
- Clean scheduling and common CFO are frozen once from the existing recordings.
  The prior clean CFO fit used the known preamble; the frozen comparison is an
  explicitly **oracle-conditioned replay bound**, not a blind receiver result.
- No noisy payload error count, header, sync or CRC chooses timing or alignment.
  **CRC-failed and sync-failed trials remain in the BER denominator.**
- Nonfinite or incomplete IQ is unscorable and recorded as an erasure, not a
  correct bit or a silently discarded failure. All actual pilot windows here
  were scorable; the erasure paths are covered by tests.

The clean CRC-valid native bytes reconstruct a **replay body reference** only.
Body disagreements, exact sync, and scheduled body CRC32 are recorded separately.
They are not independently verified live payload BER or over-the-air packet
success. Scheduled frame pass here means exact scheduled sync plus header/body
CRC32; it does not prove native CRC16/application acceptance. The normal clean
captures had already passed those checks.

Differential BER scores original preamble data bits. The coherent panel scores
transmitted phase-state bits; it does **not** silently treat coherent detection
of a differentially encoded stream as original-data decoding.

## Noise and energy convention

The source files contain four-second, 48 ksample/s complex excerpts after the
original receiver's analog, FPGA and offline decimation filters. Their hashes and
full-IQ provenance are in [manifest.json](manifest.json). Compressed NPZ inputs
preserve the original excerpt arrays exactly; the large full captures remain in
the bench archive.

Mean observed preamble energy per symbol, minus measured idle sample power, is
normalized to one. New circular complex white noise is inserted **at that digital
replay plane, before final rectangular symbol integration**: total complex
variance `N0`, `N0/2` per real dimension. The final integrator has unit-energy
weights `1/sqrt(40)`.

The originally recorded noise is retained. Added variance is
`10^(-EbN0_dB/10) - estimated_existing_matched_filter_noise_variance`; targets
cleaner than the original are rejected. The largest original-noise correction is
only **5.38e-6 of the 12 dB target noise variance**. Existing colored noise is
fixed across replays, not regenerated; this correction does not turn a capture
into a calibrated analog noise measurement.

The fast frozen sweep injects noise into matched-filter **sufficient statistics**.
For new white noise and disjoint rectangular integration windows, this is exactly
equivalent to sample-domain injection with frozen CFO/timing. A test checks the
sample-domain projection and noise variance. It avoids drawing 40 samples per
symbol when their sum is the only statistic used. The synchronization pilot does
inject sample-domain noise over the full four-second excerpt.

This does not model noise before the original physical receive filters, establish
receiver noise figure/sensitivity, or calibrate RF Eb/N0. Existing signal filtering,
phase/amplitude variations and quantization are retained as part of the waveform.
No per-symbol signal normalization or phase repair removes those effects.

## Receiver variants

1. **Frozen CFO/timing differential:** supplied clean common CFO and one timing
   selected on the clean training region; unmodified `real(z[k]*conj(z[k-1])) < 0`
   decisions, no CRC gating.
2. **Coherent nearest-center bound:** two clean training state means, frozen phase,
   CFO and timing. Scores phase symbols, not differentially decoded data.
3. **Squared-IQ scheduled pilot:** the normal estimator's square/FFT operation and
   four-second observation, followed by a timing search using only known training
   bits. It replaces the live decoder's CRC-driven timing acceptance so failures
   survive. Scheduled burst location is supplied; it is not blind acquisition or
   a faithful clone of the live acceptance policy.
4. **Learned-template scheduled pilot:** the paper's preamble ML periodogram and
   parabolic interpolation adapted to a **64-symbol non-antipodal template learned
   from the clean capture**. Scheduled preamble timing and clean state means are
   supplied. This is an offline prototype, not a deployed or blind receiver.

The template comparison changes both the estimator information and its observation
window (64 scheduled symbols versus the squared estimator's four seconds). It is
not an ablation proving which change accounts for each part of the improvement.
Added noise is white after the original receive filters, so absolute pilot
acquisition thresholds also need validation with pre-filter noise injection.

## Main findings

At normalized replay **8 dB**, with **1,104,000 scored bits per frozen curve**:

| Case | Errors | BER |
| --- | --- | --- |
| Ideal coherent BPSK, direct/phase bits | 215 | 0.00019475 |
| Ideal DBPSK, random data | 1,001 | 0.00090670 |
| 135° rectangular model, differential data | 17,635 | 0.01597373 |
| LibreSDR 1, frozen differential | 19,563 | 0.01772011 |
| LibreSDR 2, frozen differential | 19,472 | 0.01763768 |
| Pluto 0 dB, frozen differential | 18,523 | 0.01677808 |
| Pluto 20 dB, frozen differential | 18,997 | 0.01720743 |

The ideal references agree with theory: among points with at least 100 expected
and observed errors, the largest relative mismatch is **2.9%**, at most **2.06
trial-block standard errors**. Sparse high-SNR tails are not treated as validated.

Coarse log-BER interpolation on the **2 dB grid** places hardware frozen
DBPSK BER `1e-3` at about **11.7–11.8 dB**, versus ideal DBPSK theory **7.93 dB**:
roughly **3.8–3.9 dB extra for this preamble and detector**. This is a digital
replay operating-point estimate, not calibrated sensitivity or a universal
transmitter loss. The 135° model is close, but its interaction with the current
differential decision rule is not an irreducible modulation penalty. For example,
the ideal two-state coherent distance factor is `sin²(135°/2) ≈ 0.854`, only
about 0.69 dB in that different receiver model.

At 8 dB, Pluto 20 dB differential errors split into **592/552,000 no-change bits
(0.107%)** and **18,405/552,000 phase-change bits (3.334%)**. The 135° model shows
the same asymmetry. Thus preamble BER cannot be inserted into an IID packet formula
for the heartbeat's largely zero-valued body; bit pattern and correlation matter.

At 8 dB, Pluto's **scheduled pilot** gives BER **0.19366** with squared-IQ CFO
versus **0.01779** with the learned template, near its frozen result **0.01721**.
Exact scheduled sync occurs in **46/150** versus **88/150** trials. Scheduled
sync-plus-CRC32 counts are only **3/150** versus **6/150**: those small counts do
not establish a reliable packet-success improvement. Wilson intervals are saved.

In the **paper model** at 8 dB, the 16-symbol preamble gives **52,326/1,152,000**
errors (0.04542), versus **226/1,152,000** (0.0001962) for 64 symbols. This supports
the paper's known-preamble synchronization result under its own ideal waveform
assumptions. The hardware's longer transmitted preamble alone does not make the
squared-IQ estimator equivalent to that receiver. A finite-SNR penalty is not
called an irreducible asymptotic error floor.

## Confidence and reuse limits

BER intervals use independent **noise-trial blocks**, allowing correlation among
bits in one trial. They are conditional on each fixed captured waveform, not
confidence intervals across new hardware transmissions, temperatures or channels.
Nonzero-error intervals are normal cluster intervals; points with fewer than 100
errors are flagged sparse. For zero errors, the conservative one-sided upper
bound uses the number of independent trials: BER is no larger than the chance of
any error in a trial. Zero points are omitted from logarithmic plots and their
counts/bounds remain in CSVs. Sync/frame intervals use Wilson binomial intervals
across independent injected-noise trials.

Only **four original hardware bursts** underlie these replays. Repeating their
known preamble with new noise is not a million new independent source bits or
an over-the-air BER qualification. Pluto continuity was not timestamp-verified.
Rayleigh fading, drifting Doppler, arbitrary independent payload truth, and live
receiver sensitivity remain future work.

## Reproduce or inspect a failed decode

Requires Python 3 and NumPy; Matplotlib is needed only for plots. Run from this
folder. Use a **new output directory**, since completed outputs are not replaced.

```sh
python3 -m unittest discover -p 'test_*.py' -v
python3 experiments.py --output /tmp/bpsk-offline-replay
python3 analyze_results.py /tmp/bpsk-offline-replay
python3 plot_results.py /tmp/bpsk-offline-replay /tmp/bpsk-offline-plots

python3 diagnostic.py --capture pluto20 --mode square
python3 diagnostic.py --capture pluto20 --mode template
python3 diagnostic.py --capture pluto20 --mode frozen
```

`--iq noisy.npy` supplies another scheduled IQ array in the original capture's
units; `--normalized` instead accepts unit-energy replay units. `--output` saves
JSON without overwriting an existing file. Returned decision bits, error positions,
CFO, timing, sync and CRC observations survive failed CRCs. In the compressed
pilot ledgers, `decisions_hex` packs all logical decisions; bit 0 is explicitly
listed as unobserved.

The shipped `*-summary.csv` and `*-seeds.csv` retain exact counts, budgets and
intervals. [clean-symbols.csv](clean-symbols.csv) and
[frozen-references.json](frozen-references.json) identify the frozen calibration.
`fast-error-counts.npz` and `paper-error-counts.npz` retain per-trial counts.
The two `*-diagnostic-trials.jsonl.gz` ledgers retain every pilot's decisions and
known-bit error positions, including CRC failures. Full fast packed error masks
remain in the bench archive with their hash in [analysis.json](analysis.json);
`experiments.py` regenerates them. Input and public binary hashes are recorded in
[publication.json](publication.json).

[Back to investigation](../../../README.md)
