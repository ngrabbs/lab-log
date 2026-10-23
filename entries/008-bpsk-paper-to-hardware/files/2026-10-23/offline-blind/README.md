# Capture-holdout acquisition test — 2026-10-23

This is an offline extension of the [paper comparison](../offline-ber/README.md).
The previous learned-preamble pilot knew each test recording's start and learned
its template from that recording. This experiment removes those two aids.
All source captures remain unchanged; there was no hardware access or RF activity.

## Frozen receiver and split

`libre01` supplies the only learned complex state means, using the earlier
clean-reference training procedure. Their ratio removes training amplitude/global
phase. The receiver is passed **only the entire IQ array and model.json**; it does
not receive a capture name, timestamp, timing, CFO, expected body, or sequence.
`libre02`, `pluto00` and `pluto20` supply no learned parameters. This is a
**retrospective capture holdout**: these recordings were already examined in the
previous investigation. It is not a prospective test on previously unseen RF data.
The three test recordings include another LibreSDR burst and two Pluto gain settings.

The sample rate (48 kHz), symbol rate (1,200/s), 0x55 preamble, sync word and fixed
808-symbol heartbeat framing remain known protocol information. Search range is
fixed at ±12 kHz. The receiver searches every 1,280-sample window of each complete
192,000-sample excerpt for a periodic 64-symbol template; it evaluates all four
symbol phases with a 65,536-bin FFT. It keeps three separated peaks from the best
window, tries ±4 Hz offsets, then correlates over **all integer sample starts**
where a complete frame fits. The masked correlation uses symbols 0–63 and the
known sync at 256–287, fitting an unknown complex scale through correlation magnitude.
Frequency is refined locally at the selected candidate (1 Hz then 0.1 Hz grid),
then start is searched again. The normalized correlation threshold is fixed at
0.04. No CRC gate or expected payload selects a candidate. Candidates with bad sync
or CRC still return their decisions. This is a bounded coarse-to-fine search,
not an exhaustive joint timing/frequency maximum-likelihood solution.

The repetitive preamble alone cannot identify the beginning of a frame. The
unique sync participates in the masked correlation. Bits 68–251 do not enter
that final masked fit, but the initial periodic-window search can observe them.
Reported preamble BER is therefore **conditional on acquisition of this known
preamble**, with acquisition selection effects; it is not independent unknown-data
BER or an unbiased payload-BER qualification. The 392 body bits are compared only
to a clean-decode replay reference, since independently saved original body bytes
are unavailable.

## Evaluation budget and scoring

The fixed model declares three seeds (73191–73193), ten trials per seed at each
of 8 and 12 dB: 30 trials per capture/point, 180 noisy held-out trials total.
Each trial circularly shifts the entire excerpt by a uniform integer −40,000 to
+40,000 samples, adds a CFO shift uniform ±1,500 Hz and phase uniform ±π, and
scales signal plus noise by gain 2^U for U uniform [−1,1]. The heartbeat always
fits; the circular seam is in the idle portion. The receiver is not told these
values. Three untouched clean held-out excerpts are also searched.

The **evaluation harness only** uses old clean reference timing/CFO/energy to
construct controlled noise and evaluate outputs. It calls `freeze()` outside the
receiver; it passes none of that reference object to `acquire(iq, model)`.
Complex white noise is injected at the previously normalized 48 kHz sample plane,
after the original RF/digital receive filtering. This is normalized replay Eb/N0,
not measured RF Eb/N0, sensitivity or a calibrated analog noise source.

A candidate is aligned if its start is within 20 samples (half a symbol) of the
frozen clean reference plus injected delay. This truth check happens **after**
receiver output. Wrong-start candidates, below-threshold misses, exact-sync counts
and sync-plus-CRC frame counts remain separate. Only aligned candidates contribute
184 known preamble bits to conditional BER. Wrong-start decisions and their error
counts remain in the ledger; they are neither quietly discarded nor assigned an
invented aligned BER. All frame fractions use all 30 trials as denominator.

There are 30 independent four-second complex Gaussian noise-only controls; the
single clean training check is excluded from held-out results. `lock.json` records
receiver and model SHA-256 hashes taken before the final run and checked after it.
No thresholds, templates or search ranges were adjusted to improve held-out results.

A numerical issue found in synthetic tests during the initial evaluation allowed
nearly zero correlation-window energy to create impossible scores above one.
The initial run was superseded in full after adding zero-input/near-zero-energy
and flat-peak guards. The same frozen model and noise seeds were rerun. Five
behavioral tests now cover both CFO signs, unknown delays/gain/phase, missing truth
inputs, invalid/zero input, and decision retention when CRC fails. This repair
addresses numerical validity, not tuning against held-out BER.

## Results

See [summary.csv](summary.csv) for all counts, [intervals.csv](intervals.csv) for
Wilson acquisition/frame intervals and trial-block BER intervals, and
[trials.jsonl](trials.jsonl) for every trial, returned decision, nuisance parameter,
truth residual and failure. [validation.json](validation.json) records independent
recounts from the decision hex. Sparse BER tails and only three independent RF
bursts limit inference. Repeated injected-noise trials are conditional on those
fixed waveforms; they do not supply 180 independent hardware/channel realizations.

| Held-out capture | Replay Eb/N0 | Correct start / all | Wrong start | Exact sync / all | Sync + CRC / all | Preamble errors / aligned bits (BER) |
| --- | --- | --- | --- | --- | --- | --- |
| libre02 | clean | 1/1 | 0 | 1/1 | 1/1 | 0/184 (0%) |
| libre02 | 8 | 26/30 | 4 | 14/30 | 0/30 | 88/4784 (1.839%) |
| libre02 | 12 | 28/30 | 2 | 27/30 | 22/30 | 3/5152 (0.05823%) |
| pluto00 | clean | 1/1 | 0 | 1/1 | 1/1 | 0/184 (0%) |
| pluto00 | 8 | 30/30 | 0 | 20/30 | 2/30 | 88/5520 (1.594%) |
| pluto00 | 12 | 29/30 | 1 | 27/30 | 24/30 | 1/5336 (0.01874%) |
| pluto20 | clean | 1/1 | 0 | 1/1 | 1/1 | 0/184 (0%) |
| pluto20 | 8 | 28/30 | 2 | 21/30 | 0/30 | 71/5152 (1.378%) |
| pluto20 | 12 | 25/30 | 5 | 25/30 | 23/30 | 4/4600 (0.08696%) |

All three clean held-out excerpts acquire and pass sync/CRC with zero known
preamble errors (552 total scored bits). Clean CFO residuals are below 0.34 Hz.
At 8 dB, correct starts are 26/30, 30/30 and 28/30; conditional preamble BER is
1.84%, 1.59% and 1.38%. Frame success is only 0/30, 2/30 and 0/30. At 12 dB,
frame counts rise to 22/30, 24/30 and 23/30, but wrong starts still occur in
2/30, 1/30 and 5/30 trials respectively. There are no below-threshold misses in
this budget. A returned candidate is therefore not equivalent to successful
acquisition or a valid frame. The Pluto20 non-monotonic start counts emphasize
that this small budget and local search do not establish a smooth acquisition curve.

The 14 noisy wrong-start candidates are displaced by 3,040–17,496 samples;
these are frame-boundary mistakes, not marginal half-symbol timing decisions.
One has a CFO error near −305 Hz, consistent with a periodic-preamble alias.
The others have residual CFO about 1–3 Hz. Aligned candidates reach a maximum
absolute CFO error of 4.72 Hz. Correlation/window ambiguities and local refinement
remain plausible failure mechanisms; this experiment does not isolate their
individual causes. All wrong candidates fail sync/CRC and remain in the results.

No noise-only control emitted a candidate (0/30 four-second windows). The
one-sided 95% upper bound is still **9.50% per window**; this small control budget
cannot qualify an operational false-alarm rate. Threshold selection used no
held-out outcomes. Five behavioral tests pass and the saved decision bytes
independently reproduce all recorded preamble/body error counts and CRC outputs.

This supports the paper's preamble-aided frequency-estimation approach across
recordings without supplying the answer. It does **not** remove the approximately
135° waveform/current differential-detector penalty seen in the prior frozen
comparison: acquired 8 dB trials remain around percent-level preamble BER. The
new sample sizes, acquisition selection and nuisance randomization differ from
the earlier scheduled pilot; those BER values are context, not a paired statistical
improvement claim. Frequency/timing acquisition remains a separate reliability
problem, so this prototype is not ready to replace the ground-station receiver.
Next, freeze a revised ambiguity-resolution method using training data only and
reserve genuinely new captures with independently saved transmitted payloads for
prospective testing. Pre-filter noise and continuous-stream false-alarm testing
remain necessary before RF sensitivity or live-receiver claims.

## Reproduce offline

Keep this directory beside `offline-ber/` so the four published waveform NPZs,
manifest and shared diagnostic module resolve. Python 3 and NumPy suffice:

```sh
OPENBLAS_NUM_THREADS=1 python3 -m unittest discover -s . -p 'test_receiver.py' -v
OPENBLAS_NUM_THREADS=1 python3 run.py
python3 analyze.py
```

For a single unassisted decode, run `python3 decode.py ../offline-ber/pluto20-48k.npz`.

Run from this directory. `run.py` replaces derived trial/count/lock files; archive
results first if retaining multiple runs. It never writes source NPZs. Model and
receiver remain fixed; `prepare.py` documents how the model was derived solely
from `libre01` and need not be rerun. JSONL decisions/metric/counts should reproduce;
elapsed wall times vary. `publication.json` hashes the published source/results.
