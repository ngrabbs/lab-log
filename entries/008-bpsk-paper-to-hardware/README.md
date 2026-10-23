# 008 BPSK: from the communications theory paper to the bench

**Status:** In progress  
**Started:** 2026-10-23  
**Updated:** 2026-10-23

Over the summer I took ECE-4813 Communications Theory and wrote a paper about a
Doppler-affected UHF BPSK satellite link. The intended application was the
transceiver I was designing. The hardware now sends packets back to my ground
station successfully. I want to find out how the working link relates to the
model: where the predictions hold, where the receiver behaves differently, and
what measurements would explain the difference.

This entry is the **test plan**, not a new set of bench results. The earlier
[transceiver bring-up](../003-ember-transceiver-bringup/README.md) is the starting
evidence. New measurements and failed attempts will be added here as the tests
are performed.

## What I want to learn

1. How close are the transmitted phase states to ideal BPSK, and what does the
   actual waveform cost in noise margin?
2. Does measured BER follow the appropriate theoretical curve once the receiver,
   noise bandwidth and energy-per-bit definitions match?
3. How much frequency offset can the link acquire, and how much *residual* offset
   can it tolerate after acquisition?
4. Do longer packets fail because of independent noise errors, synchronization
   loss, phase drift, or transmitter/receiver timing?
5. Can measured power, sensitivity and frequency tolerance replace the assumed
   numbers in the paper's practical link budget?

The first useful outcome is a measured baseline and an explanation of its largest
departure from the model. A complete satellite qualification is outside this
investigation.

## What matches the paper, and what does not

The reviewed paper source is *Performance Analysis of a Doppler-Affected UHF BPSK
Satellite Link with Frequency-Offset Compensation*. Its MATLAB driver uses eight
samples per symbol, unit-energy rectangular pulses, AWGN and flat Rayleigh
channels. It compares coherent detection with no offset, no compensation, and a
known-preamble frequency estimate followed by one phase correction. The principal
comparisons use 16/64 preamble symbols and 64/256/1024 data bits. The source
versions are identified in [the provenance record](files/source-notes.md).

| Item | Paper model | Reviewed hardware/software path | Consequence for the test |
| --- | --- | --- | --- |
| TX waveform | Ideal antipodal rectangular BPSK | Si5351A → XOR → tripler → RF filters/amplifier → antenna switch | Measure phase separation, amplitude imbalance and transitions first. |
| Bit mapping and detection | Direct coherent symbol decisions | Differential encoding; ground decoder integrates symbols and decides from adjacent-symbol products | Use the DBPSK baseline for the operational receiver; keep coherent results separate. |
| Frequency estimate | Known preamble removed, then FFT peak/interpolation | Ground decoder squares IQ, estimates the doubled carrier, then derotates | Compare algorithms on the same recordings. Longer transmitted preamble does not automatically lengthen this decoder's estimator observation. |
| Preamble | 16 or 64 known pseudorandom symbols | 32 bytes of `55`, or 256 symbols | A paper-equivalent replay needs its own known preamble, not a silent change to the live frame. |
| Packet | Ideal known data, boundaries supplied | Sync `1ACFFC1D`, version 3, sequence, length, native packet, outer CRC32, guard | Separate acquisition, BER, frame integrity and application delivery. |
| Channel knowledge | Exact timing; perfect CSI in Rayleigh baseline | Finite timing search, independent clocks, actual filters and ADC | Measure these effects; a room is not a controlled Rayleigh channel. |

The ground decoder is `ground/bpsk/modem.py`; the current transmitter framing is
in `firmware/transceiver/bpsk_packet.h`. The supplied local `firmware/comms/`
directory describes an older runtime and is not the full current packet path.
The separate `ground/uhf/` FSK demo is not a BPSK reference.

Earlier entry 003 records 185/185 packets in an 11.5-minute demonstration and
nonideal phase steps around 90° at 2 mA and 135° at 4 mA in earlier measurements.
Those are historical observations, not a measurement of today's setup. Successful
short-range decoding does not establish the expected BER curve. The user now
reports receiving packets successfully; record the exact direction and firmware
again at the start rather than assuming the older board-RX limitation still holds.

## Equipment and connections

Available, as reported on October 23: LibreSDR using B210/B205-compatible firmware,
Pluto, HackRF, RTL-SDR, DS1202-Z scope, TinySA Ultra and assorted attenuators.
There is no confirmed dedicated signal/noise generator. Start with LibreSDR as
the main IQ receiver. Pluto is a candidate independent BPSK source for board RX;
confirm its installed waveform tooling before the session. The other SDRs are
optional cross-checks, not prerequisites or interchangeable calibrated receivers.

Use three arrangements in order:

```text
A. Board TX → rated fixed attenuation → step attenuation → LibreSDR RX
   Swap the receiver for TinySA at the same reference plane for level checks.

B. Known SDR waveform → calibrated attenuation → board antenna/RX port
   Record board ADC samples and receive decisions; use LibreSDR separately
   to characterize the source before connecting it to the board.

C. Clean saved IQ or ideal symbols → controlled noise/CFO → offline receivers
   No RF transmission needed for this arrangement.
```

Before A/B, record the measured or conservatively bounded source power, pad power
ratings, instrument input limits for the actual ports, cable loss, DC blocking
requirements and selected reference plane. Choose total loss so the maximum
possible input stays below the lowest applicable input limit with margin. Verify
the level through the initial fixed pad before connecting the SDR. Do not infer
RF power from an SDR gain number or the amplifier's advertised capability.
Keep unused RF ports terminated appropriately. Save a connection photo and diagram
with actual pad values before enabling a finite burst.

Use the scope for GP16 bit timing, accessible baseband and supply behavior. Use
complex IQ for UHF phase-state measurements; no assumption is made that the
scope can directly measure phase accurately at 437 MHz. Use TinySA for carrier,
relative products and power checks within its verified settings and limits.
Record model/firmware, reference level, attenuation, RBW/VBW and detector. If no
traceable level reference is available, label power as estimated and retain its
uncertainty; do not turn an approximate spectrum reading into calibrated sensitivity.

Fix RX gain, sample rate, filter bandwidth, antenna/cable arrangement and clock
source within each series. Disable AGC where possible. Record actual rate/tune
readback, overflow/underflow counters, clipping, firmware identity and physical
reworks. Start with the working 1200-symbol/s configuration. Other rates are later
experiments, not assumed supported options.

## Measurements and denominators

Save original IQ, TX bytes, TX attempt outcomes and receiver logs before analysis.
The normal decoder only returns CRC-valid packets, so **its output cannot measure
raw BER**. An offline diagnostic must retain decisions from a predetermined bit
window even when sync, header or CRC fails. This diagnostic does not forward data
or weaken normal packet acceptance. Its implementation is a prerequisite for BER
runs; it is not supplied by this documentation change.

For controlled BER, use known test bits and an independent burst-time/window
manifest. Freeze timing/alignment rules on a clean baseline before the noise
sweep. Do not align every noisy packet by choosing the offset with the fewest
payload errors. Distinguish oracle timing from the operational timing search.
For live native telemetry, retain the actual generated TX bytes and sequence;
do not substitute an expected constant heartbeat for changing data.

Report these separately:

- **BER on scheduled, alignable windows:** erroneous scored bits / scored bits,
  with the number of erased/unscorable windows and acquisition coverage beside it.
  Also show BER conditioned on acquisition, explicitly labelled.
- **RF packet success:** exact expected frames recovered once / independently
  confirmed completed RF attempts. Missing, malformed and CRC-failed frames fail.
  Report admitted requests and local TX failures separately; they explain service
  reliability but are not a noise-only RF denominator.
- **Service delivery:** unique original packets reaching the application archive /
  submitted requests. Local RF completion, decoder acceptance, UDP send and archive
  confirmation are different observations. Disable retries or count every RF attempt.

For each packet, retain bit-error count and positions, burst start, CFO estimate,
residual CFO estimate, timing estimate, CRC outcomes and reason for rejection.
If a corrupt header prevents packet identity, classify the scheduled window as
failed/erased rather than dropping it. Deduplicate overlapping decode windows.
Stream gaps invalidate the affected measurement interval; retain the failed run.

Use fixed sample budgets chosen before each sweep: start with 2,000 packets per
packet-success point and 10^6 scored bits per BER point, split over at least three
independent captures/seeds. At 1200 bit/s, 10^6 payload bits already needs at least
13.9 minutes before overhead and gaps. Pilot runs can use 100 packets; do not
present them as final statistics. Plan larger fixed budgets where the expected
error count is below roughly 100. Report counts and 95% intervals, not only ratios.
For zero independent events in N trials, the one-sided 95% upper bound is
`1 - 0.05^(1/N)`, approximately `3/N`; zero observed errors is not zero BER.
Differential decisions share samples and phase slips cluster errors: use capture-
or packet-block intervals for BER rather than claiming independent bit trials.
Packet binomial intervals likewise assume independent attempts; report correlations
and capture-to-capture spread when that assumption fails.

## Test sequence

### T0 — preserve and repeat the working link

Record board ID/revision, reworks, installed firmware release/source SHA/dirty flag,
UF2 hash if available, modem revision, clock/drive settings and actual RF frequency.
Save the current known-good configuration without reflashing. Capture at least
100 bounded transmissions and compare TX bytes with RF bytes. Run a separate
TX-off capture of equal duration to check false detections and sample continuity.
If RX on the board is working, record a separate source → board receive test;
an SDR downlink capture is not evidence about the board's analog RX path.

**Proceed when:** packet identity and attempt accounting agree, sample streams are
continuous, input levels are credible and no clipping is present. A failure here
gets its own retained record before any BER interpretation.

### T1 — measure the actual phase alphabet

Capture the existing preamble and known patterns through the conducted TX path
at a comfortable nonsaturating level. Additional held-phase, all-zero/all-one,
alternating and seeded pseudorandom patterns require a reviewed bounded test
image or existing verified test command; do not invent a console command.

Estimate CFO once over a clean reference segment; remove only that common linear
rotation. Plot symbol-center IQ, amplitudes by state, phase separation and spread,
transition trajectories and adjacent-symbol phase differences. Report uncertainty
across bursts. A fitting algorithm that forces every symbol onto ±1 would hide
the defect being measured. Measure GP16 deadlines/jitter with the scope alongside
the IQ observations. Repeat the present drive setting; compare 2/4 mA only as
separate, recorded configurations if supported and electrically acceptable.

For the tripler, an ideal odd harmonic preserves antipodal states because
`3π = π (mod 2π)`; it also multiplies phase error. Actual filtering, duty cycle
and drive can change the result. This is a hypothesis to investigate, not a
diagnosis. Plot transition and steady-state behavior separately.

**Output:** waveform baseline, relative spectrum/occupied-bandwidth observations,
symbol timing and a decision on whether ideal-BPSK theory is an appropriate
reference. If the phase states are non-antipodal, retain that configuration as
the baseline and add a measured-waveform simulation; record any later repair as
a new configuration.

### T2 — controlled noise, with matched receiver comparisons

First reproduce the paper's AWGN baseline in an isolated copy of its MATLAB
sources, using the documented seed and eight samples/symbol. Do not overwrite
submitted results. Then test ideal differential symbols and a clean captured
hardware waveform at proposed `Eb/N0 = -4, -2, 0, 2, 4, 6, 8, 10, 12 dB`.
Use common noise realizations for paired receiver comparisons and independent
seeds across repeats. Apply these receiver variants offline:

| Receiver | Purpose |
| --- | --- |
| Coherent with known phase/frequency/timing | Paper's AWGN reference and waveform ceiling |
| Coherent with paper-style known-preamble estimate and one phase correction | Reproduce the paper's synchronization assumptions |
| Differential with known CFO/timing | Isolate differential detection loss |
| Current squared-carrier estimator, timing search and differential detector | Measure the operational ground receiver |

For coherent detection of a differentially encoded stream, score transmitted
phase symbols against coherent BPSK theory. If decisions are then differentially
decoded, score original data separately; the latter has a different error law.
Use paper-format direct BPSK packets to reproduce its original data-BER curves.

At zero residual CFO and ideal antipodal symbols, plot coherent
`Pb = 0.5 erfc(sqrt(Eb/N0))` and differential
`Pb = 0.5 exp(-Eb/N0)` as distinct references, with linear `Eb/N0` in both
expressions. The differential expression assumes ideal two-symbol detection;
frequency/timing acquisition and distorted phase states can add loss.
[MathWorks lists these separate cases](https://www.mathworks.com/help/comm/ug/analytical-expressions-used-in-berawgn-function-and-bit-error-rate-analysis-app.html).

For unfiltered complex samples with white noise and one bit/symbol,
`Eb/N0_dB = SNR_sample_dB + 10 log10(Fs/Rb)`.
After filtering, use the actual noise PSD or equivalent noise bandwidth, not
sample rate as a substitute. For measured power,
`Eb/N0_dB = C_dBm - N0_dBm_per_Hz - 10 log10(Rb)`; equivalently use C/N in
a documented noise bandwidth B and add `10 log10(B/Rb)`.
[The sample/SNR distinction is documented here](https://www.mathworks.com/help/comm/ug/awgn-channel.html).

Estimate signal power on active symbols after subtracting same-gain TX-off noise.
The clean capture already contains noise: add only the variance needed to reach
the target, and reject targets cleaner than the original recording. Add circular
complex noise before the modeled receive filter; document variance convention,
seed and all filtering. Do not use an `awgn` SNR argument as if it were Eb/N0.

Offline injection tests the captured waveform and software receiver. It does not
measure analog sensitivity or noise added ahead of the board LNA. Follow it with
conducted attenuation sweeps in both directions where available: proposed 3 dB
steps to locate the knee, then 1 dB near it, checking gain and clipping each time.
Without a calibrated input noise density, plot PER versus input power/loss and
leave the Eb/N0 axis unclaimed. An SDR can later generate a known signal plus
noise before the board input; characterize its DAC/RF distortion and output level
first. No standalone noise generator is required for the first stage.

**Output:** BER/PER curves, calibration uncertainty and implementation loss at a
common supported BER such as 10^-3. Separate hardware waveform loss from estimator
and detector loss. Do not extrapolate an unmeasured tail.

### T3 — separate acquisition from residual frequency error

At proposed 4, 8 and 12 dB Eb/N0, inject signed normalized offsets
`ν = Δf/Rb = 0, ±0.01, ±0.05, ±0.10, ±0.25, ±0.50`. At 1200 bit/s these are
0, ±12, ±60, ±120, ±300 and ±600 Hz. Use a broader acquisition test at
0, ±1, ±2, ±5 and ±10 kHz, only where the source, RF/baseband filters and sample
rate pass the entire shifted signal. Repeat selected points with actual source
tuning; post-capture CFO cannot test analog passband rejection or front-end capture.
Measure actual offset rather than treating a requested tuning delta as truth.

Run the paper receiver and differential receiver with correction enabled and
disabled, plus a known-CFO control. Report acquisition probability, estimate bias,
RMSE and residual distribution separately from post-acquisition BER. The current
48 ksample/s ground estimator's square-and-FFT search is nominally ambiguous
outside ±12 kHz; analog bandwidth and estimator failures may narrow that range.
This is not automatically the capture range of the board's real ADC receiver.

To isolate the paper's within-symbol result, use an explicitly **oracle**
symbol-center phase reference after integration. Its amplitude is `sinc(ν)` and
power factor is `sinc²(ν)`; at ν=0.5 the continuous-time loss is 3.92 dB. With
finite rectangular sampling, compare the exact discrete factor
`[sin(πν)/(Ns sin(πν/Ns))]²` as well, using the limit 1 at zero. This oracle
experiment differs from an uncorrected packet receiver.

A coherent receiver with a single preamble phase correction retains a phase
ramp `2π f_res t`; plot error locations down the packet. A differential receiver
instead sees approximately `2π f_res/Rb` between adjacent symbols. Its ideal
noiseless decision margin reaches zero at `|f_res| = Rb/4` (300 Hz here), before
considering integration loss or waveform distortion. This derived boundary is
a test hypothesis, not a measured tolerance or a claim that all offsets fail the
same way. Resolve frequency sign and BPSK phase ambiguity with the known preamble.

**Output:** separate capture-range and residual-tolerance plots, with the actual
received passband and correction method on each plot.

### T4 — preamble length and packet duration

In paper-equivalent replay, test preambles 16/64/256 symbols and data 64/256/1024
bits at selected near-knee noise levels and ν=0/±0.10. Hold receiver settings
fixed, then deliberately vary only the estimator's observation length. A 16- or
64-symbol prefix cut from the live `55` preamble is not the paper's pseudorandom
training waveform. Use exact known sequences and label the two experiments.

On hardware, start with the current 256-symbol preamble and existing native
packet sizes; record the exact scored field and full RF-frame length. The
reviewed transmitter permits 128 native bytes, with 63 framing/guard bytes:
191 bytes × 8 /1200 = 1.2733 seconds, including 128 guard symbols. A 1024-bit
paper payload is not a 1024-bit complete RF frame. Check the actual installed
limits before changing lengths, and retain the finite payload deadline and hard
mute. Arbitrary payload/preamble sweeps need a bounded test mode first.

Compare directly measured packet success with `(1-Pb)^Nb` only as the independent
bit approximation over the stated scored region. Full-frame delivery also
depends on preamble/sync/header/CRC acquisition; differential errors can be
correlated. Plot errors versus bit index and inter-error spacing to explain a
mismatch rather than fitting away the difference.

**Output:** useful packet length and preamble overhead for each receiver and an
explanation of any length-dependent floor.

### T5 — drifting offset, fading and board RX

These follow the static tests. Inject `exp(j 2π(f0 t + 0.5 a t²))` for proposed
rates a=0, ±50 and ±270 Hz/s. The last value is a paper-derived stress case, not
a measured orbit. A 270 Hz/s drift changes frequency by about 344 Hz across the
1.2733-second frame, so the paper's short-packet constant-CFO approximation may
be insufficient for this 1200-baud link. Compare first/middle/end residual phase,
acquisition and packet success. Even a small frequency change can accumulate
material phase over a long coherent packet.

Reproduce the paper's flat Rayleigh/perfect-CSI curve in software separately.
If adding fading to hardware IQ, specify its time correlation/coherence time and
receiver channel knowledge. A moving antenna experiment is useful afterward,
but distance and multipath are uncontrolled variables, not an exact validation
of that Rayleigh formula.

For the board RX direction, characterize the SDR source, then sweep input level,
static offset and selected drift cases through the real RF/baseband path. Record
ADC rate, bias, clipping, filter response and actual decoder. A single real ADC
channel/Hilbert reconstruction is not automatically equivalent to complex SDR IQ
or perfect carrier recovery. If firmware exposes only accepted packets, measure
PER first and add diagnostic ADC/decision logging before claiming board BER.
Repeat downlink and uplink independently; a round trip mixes both probabilities.

## Revisiting the practical conclusions

The paper's illustrative +20 dBm TX, antenna gains, losses and thermal noise
density are assumptions, not present-board measurements. Replace them with
measured antenna-port power, feed/filter/switch losses, antenna data, receiver
noise/sensitivity and their uncertainty. Report link margin at a stated BER/PER
and rate. Keep the conducted result distinct from an antenna/range test and any
orbital prediction. Include receiver noise figure/system temperature; -174 dBm/Hz
alone is not the receiver's effective noise floor.

The source's compensated-receiver approximation neglects some acquisition/phase
effects. Its semi-analytical implementation uses a high-SNR frequency-estimation
variance proportional to `1/(Eb/N0 · Np³)`, so a high-SNR finite-run flattening
should not automatically be called an irreducible asymptotic floor. Likewise the
`cos²(phase)` approximation loses the sign of a coherent decision beyond ±90°.
Use signed decision statistics and empirical phase/error plots in those regimes.

The comparison is useful even if the curves disagree. A fixed horizontal loss
can suggest waveform/filter/noise-calibration issues; failure only before
acquisition suggests estimator range; errors accumulating late in coherent
packets suggest residual drift; changes with drive suggest modulation quality.
These are hypotheses to test one at a time, not conclusions from packet success.

## Current outcome and next session

The plan and source comparison are complete; experimental work remains **In
progress**. No new transmission, firmware change, calibration or BER measurement
was performed while writing this entry.

First session: preserve the current working configuration, photograph the
conducted setup, establish reference-plane levels, repeat T0 and capture T1 IQ.
Then add offline raw-decision logging and run T2. This order provides useful
results before implementing variable preambles, a new receiver or a noise source.

Use the [session worksheet](files/session-template.md) and
[empty measurement table](files/measurements.csv). Keep large original IQ files
in durable storage, record hashes and capture metadata, and link selected plots
here beside the measurements they explain. Never replace original captures with
noise-injected or corrected derivatives.

[Sources and revisions](files/source-notes.md) ·
[Related bring-up](../003-ember-transceiver-bringup/README.md) ·
[Back to Lab Log](../../README.md)
