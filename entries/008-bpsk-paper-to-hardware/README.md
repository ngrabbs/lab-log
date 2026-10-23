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

This entry combines the **test plan** with conducted spectrum checks, two
LibreSDR IQ heartbeat captures, a Pluto cross-check, a Pluto gain check and an
offline BER comparison with the paper. The earlier
[transceiver bring-up](../003-ember-transceiver-bringup/README.md) is the starting
evidence. Proposed tests remain distinct from the dated results.

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

The shared [equipment inventory](../../equipment/README.md) is the reference for
this investigation. Use LibreSDR with the installed B210/B205-compatible image as
the main IQ receiver and Pluto as the candidate independent BPSK source for
board RX. HackRF and RTL-SDR are optional cross-checks. Record exact installed
images and verify Pluto waveform tooling before the session.

The inventory also lists a NanoVNA-F V2, Rigol DS1202Z-E scope, Analog Discovery,
Nooelec 1/2/3/6/10/20 dB pads, PCB attenuator boards, BECEN DC blocks, DMMs and
bench supplies. The Analog Discovery generation is unconfirmed; use it as an
optional logic/baseband capture tool only after identifying its inputs and limits.
Use the DMMs for board-rail checks and the current-limited supply for powering the
existing configuration. No additional amplifier is needed for the initial tests.

A standalone RF signal generator was reported available in an earlier entry,
but its model, UHF coverage, output accuracy and current availability are
unconfirmed. It is an optional tone source after those details are established,
not a prerequisite. No dedicated calibrated noise source is established by the
inventory; retain offline noise injection and the SDR-generated waveform route.

The [May 17 attenuator characterization](../../equipment/characterizations/attenuators/README.md)
includes original Touchstone files. At the saved 434.8089 MHz sample, the nominal
20+10 dB chain has 29.56 dB loss, and the all-six chain has 41.13 dB loss
(nominally 42 dB despite its historical “41dB” filename). These are historical
low-power VNA measurements near the band, not current 437 MHz calibration or
proof of power handling. Pad identity, cables, reference planes and uncertainty
must be established for the actual assembly.

Use the NanoVNA with a fresh through/response calibration appropriate to the
measurement, preferably a full two-port calibration where supported, to measure
S21 of each intended pad/cable/DC-block chain at the actual TX/RX frequencies.
Save the new calibration description and Touchstone data separately from the
May files. Verify DC-block passband rather than assuming it from the inventory's
upper-frequency rating. With all active sources disconnected, the VNA can also
characterize suitable passive filter/antenna paths; document bias isolation and
do not connect it to a live transmitter. The historical files' zero-filled S12
and S22 are unavailable measurements, and their unresolved S11 excursions are
not a certified match specification.

Use three arrangements in order:

```text
A. Board TX → rated fixed attenuation → selectable fixed pads → LibreSDR RX
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
Use a suitable 50 Ω UHF termination for ports that require it. The inventory's
Pacific Antenna dummy load is listed for DC–50 MHz; do not assume it is a
437 MHz load. Save a connection photo and diagram
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
or weaken normal packet acceptance. The [offline diagnostic and replay results](files/2026-10-23/offline-ber/README.md)
now implement that distinction; the normal live decoder remains unchanged.

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
steps to locate the knee, then about 1 dB near it, checking gain and clipping each
time. Use measured combinations of the available fixed pads; a calibrated step
attenuator is not assumed. Stop TX before changing connections, record the actual
total chain loss for each point, and recheck the baseline after reconnecting.
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

## October 23 — first conducted spectrum check

With the transceiver off, I removed the antenna from J9 and assembled the
Nooelec 20/10/6/3/2/1 dB pads with one DC block at the 20 dB end. I calibrated
the NanoVNA over 430–440 MHz and saved it to slot 0. The assistant read the USB
console and collected the measurements. No calibration slot was overwritten.

The instrument identified itself as NanoVNA-F V2, firmware 0.5.4, with 101 points.
It reported open/short/load/thru calibration applied. The initial console read
returned noise-like S21 while only an S11 display trace was enabled. Switching
that trace to S21 produced the through results below; the first read was not
accepted as a cable-loss result.

| Connection / quantity | Recorded result |
| --- | --- |
| Cables joined by through adapter, three reads | S21 −0.071 to +0.099 dB over 430–440 MHz |
| DC block plus all six pads, five reads, 435 MHz | Mean attenuation 41.355 dB |
| Same assembly, 437 MHz | Mean attenuation 41.384 dB |
| Same assembly, all five reads over 430–440 MHz | Attenuation 41.233–41.552 dB |

The through check is consistent with the saved calibration, not an independent
absolute-accuracy verification. These readings establish assembled-chain UHF
loss, not the DC block's isolated loss or the pads' power handling. The historical
May chain measurement was a different setup and is not subtracted to estimate
DC-block loss. [Forward S21 data](files/2026-10-23/vna-s21.csv) retains every read.

I moved the complete assembly to J9 and connected the 1 dB end directly to the
TinySA RF port. The transceiver and IHU were powered, with LibreSDR disconnected.
Additional adapter details and current supply readings were not separately
recorded. TinySA identified firmware `tinySA4_v1.4-156-g4eb315d`, hardware
V0.4.5.1.1. IHU identified version 0.15.0, clean source
`701e96c00c8a9a207d29a746eee74c7108a2a1b3`; this does not identify the installed
transceiver firmware. The IHU had no outstanding UHF requests, retained a previous
faulted-run state, and reported three older faults. Those records were preserved.

A receive-only survey used input mode, LNA off, zero external gain correction,
100 kHz RBW and 430–440 MHz. The first idle survey used 30 dB internal attenuation.
For the burst test, internal attenuation was reduced to 10 dB and a fresh baseline
was taken at that setting. No TinySA level calibration or firmware change was made.

### The failed recorder attempt

One heartbeat request was sent, but the first recording script aborted when a
scan yielded 100 parsed points rather than the expected 101. It failed before
saving its in-memory spectrum and console replies. There is no usable burst
spectrum or retained completion reply for that attempt; it is not counted as a
successful captured measurement. The cause of the incomplete scan is unresolved.

The recorder was changed to stream JSONL records immediately, retain incomplete
sweeps without inventing missing points, and save errors and command-write events.
A receive-only check completed 14/14 sweeps with no RF-producing commands.
I then explicitly authorized one additional heartbeat. There were no automatic
retries.

### The saved heartbeat capture

The corrected run wrote **one** `uhf heartbeat` command. The IHU reported:

```text
SUBMITTED request=16 type=128 bytes=38
UHF request=16 outcome=QUEUED status=0 bytes=38 digest=152a17f7 ground_ack=0 outstanding=1
UHF request=16 outcome=RF_TX_COMPLETE status=0 bytes=38 digest=152a17f7 ground_ack=0 outstanding=0
```

All **44/44 sweeps** had the complete 101-point grid. Four preceded the command;
40 covered the subsequent eight-second window. Three sweeps sampled the strong
437 MHz signal at approximately −29.41, −29.91 and −29.41 dBm at the TinySA
input. Later sweeps returned to the idle level. IHU pending and UHF-pending
counts ended at zero; matched replies increased from 28 to 30. CAN error
registers and RX overflow stayed zero, while the pre-existing lifetime TX-failure
count remained 3. Local RF completion is not a ground acknowledgment.

![Measured spectrum and 437 MHz level during one conducted heartbeat](images/heartbeat-spectrum-02.svg)

The upper plot is calculated from saved sweeps, not an instrument max-hold
screenshot. Horizontal bars in the lower plot show sweep intervals; the individual
437 MHz sample occurs somewhere within each interval. The 100 kHz frequency grid
and RBW only locate the burst near 437 MHz. They do not resolve exact CFO,
phase-state quality or occupied bandwidth.

Using the strongest input reading and the measured external loss gives:

```text
estimated J9 level = −29.406 dBm + 41.384 dB = +11.978 dBm ≈ 15.8 mW
```

This is a **rough in-band level estimate**, not calibrated total modulated output
power. It uses a swept detector sample, with TinySA absolute calibration accuracy
and reconnection uncertainty unestablished. The instrument's displayed input
level already accounts for its internal attenuator; the 10 dB internal setting
is not added again. No packet was decoded by the TinySA and no BER/PER or ground
delivery result is inferred.

[All saved sweep levels](files/2026-10-23/heartbeat-spectrum-02.csv) ·
[IHU replies, board hardware ID redacted](files/2026-10-23/heartbeat-spectrum-02-ihu.txt) ·
[Settings, input hashes and derivation](files/2026-10-23/session.json) ·
[Plot reproduction script](files/2026-10-23/plot_capture.py)

Original captures remain unchanged in the local bench archive. Published CSVs
are explicitly derived exports; the session file records their original input
hashes. The failed first attempt is retained as an error record, not reconstructed
as a successful capture.

## October 23 — LibreSDR IQ capture and first phase estimate

The LibreSDR did not enumerate on the controller host. Restarting only the USB
controller with no enumerated devices brought back a hub but not the radio; the
other controller, carrying the mounted backup drive and consoles, was not reset.
The cause of that USB failure was not established. Moving to the ground station
allowed enumeration. UHD initially lacked its image-directory setting; using the
existing image files restored discovery. The FPGA SHA-256 matched the installed
capture helper's expected value. The hardware probe passed register loopback and
reported USB3 operation, firmware 8.0 and FPGA 16.0.

I connected the existing measured assembly to the radio's physical **RXA** port,
leaving the transceiver off initially. Reported connector labels are TXRA, RXA,
RXB and TXRB. The ground station's idle `ember-fire-uplink.service` was temporarily
stopped so it could not compete for or transmit through the radio during the
bench work. Its prior active state was recorded for restoration after the session;
unit configuration and enablement were unchanged.

Two receiver-preparation attempts failed before any stream started: a Python
getter needed an explicit motherboard argument, then UHD rejected a 49.152 MHz
master clock for simultaneous dual RX. These distinct error reports and empty
arrays are retained, not presented as noise measurements. With the getter corrected
and a 30.72 MHz clock, the five-second idle baseline completed at nominal
192 ksample/s on both channels, gain 0 dB, RX2 selection, AGC disabled and 200 kHz
analog bandwidth. No UHD errors or timestamp gaps were detected.

After I powered on the transceiver, the assistant started a bounded two-minute
dual-channel recording and, with explicit authorization, sent exactly one
heartbeat request through the IHU. The receiver itself used no TX API and
forwarded nothing. A fresh CAN HELLO confirmed the peer before the request.

| Observation | Result |
| --- | --- |
| Recorded IQ | 120 seconds, 23,040,000 complex samples per channel |
| Receiver settings | 437 MHz requested, nominal 192 ksample/s, gain 0 dB, RX2 selected on channels 0/1 |
| Clock / bandwidth readback | About 30.72 MHz master clock; 200 kHz analog bandwidth |
| Stream integrity | No reported UHD errors or detected timestamp gaps; no nonfinite samples |
| Near-full-scale check | Zero I/Q components at or above the explicit 0.99 criterion |
| IHU request | Request 18, 38 bytes, QUEUED then RF_TX_COMPLETE, digest `4104665e`, ground_ack=0 |
| Strong receive path | Physical RXA → UHD channel 0 with this FPGA and RX2 selection |
| Burst interval | Approximately 68.28–68.97 seconds into the capture using a 10 ms block-power threshold |
| Normal decoder | One HEARTBEAT recovered on channel 0, outer RF sequence 18, native sequence 14 |
| Source comparison | Recovered native length 38 and CRC32 `4104665e` match the IHU report |
| Channel 1 | A much weaker copy of the same frame also decoded; this is not another transmission |

The decoder's normal `dbpsk` path was used, with no phase-diagnostic fallback.
It validated the outer frame CRC32 and the native packet CRC16. The IHU console
retained the transmitted length and digest, not the full transmitted byte string:
this establishes a matching length/digest, rather than an independently saved
byte-for-byte TX/RX comparison. Nothing was forwarded to Yamcs, and no RF ground
acknowledgment was transmitted.

Both channels saw the same burst, but channel 0's peak 10 ms block power was about
32 dB above channel 1's. The unconnected second input's recovery may reflect
coupling/leakage; the mechanism is unmeasured. Do not count these copies as two
packets or infer isolation from a calibrated two-port measurement.

### Frequency and phase observations

The normal ground decoder estimated **−7347.20 Hz** relative to the requested
437 MHz receiver center on channel 0. That is an uncalibrated relative CFO estimate,
not a precise absolute TX-frequency measurement or evidence of Doppler on this
stationary bench. Its raw normalized offset is approximately **−6.12** at
1200 symbols/s, well outside the paper's residual-offset sweep of 0–0.5. The
working receiver removes bulk CFO before integrating symbols, so the raw offset
must not be inserted into the paper's post-correction BER curve.

![IQ power on both channels and the measured preamble phase states](images/iq-heartbeat-01.svg)

The phase estimate uses 248 known preamble symbols, omitting four at each end.
After the normal decoder's single carrier correction, timing candidates were
compared using within-state variance on the known preamble. Each candidate used
the central 8 of 40 samples per symbol. The best candidate gave **134.16°** between
the two complex state centers. Fitting one additional common linear phase slope
across the preamble changed that to **134.14°**, with a state-amplitude ratio of
about **1.105**. The fitted additional slope was about +0.76 Hz; it is an offline
training-based refinement, not a change to the operational receiver or a verified
frequency standard.

The plotted points use that one common frequency refinement and one global
rotation/scale. The two state centers remain independent and are not forced
antipodal. Within-state phase standard deviations after refinement were about
9.7° and 9.8°; these describe this preamble, not independent-trial uncertainty.
An earlier full-symbol average at the first CRC-valid timing produced about
121°, illustrating how integration-window placement and transition mixing can
bias a phase-state estimate. This is why neither number is treated as a direct,
calibrated RF phase measurement at J9.

The approximately 134° steady-symbol estimate is consistent with the earlier
non-antipodal observations in entry 003. It explains why successful differential
decoding is not sufficient evidence of ideal 180° BPSK. Current drive strength and
the responsible circuit stage were not measured in this session; a cause is not
assigned. No BER is inferred from one CRC-valid heartbeat.

### CAN observation retained separately

The IHU's lifetime TX-failure count increased **3 → 4** during this run. TEC
was 7 immediately afterward and returned to zero on a later read-only status
check; REC, EFLG and RX overflow were zero. The later fault report retained a new
code-3 record at uptime 94,251,323 ms. The requested RF packet nevertheless
received a local RF_TX_COMPLETE reply and was decoded from IQ. Cause and
repeatability of the CAN failure remain unresolved. No counter was cleared and
no automatic RF retry was issued.

The finite receiver stream stopped after its full sample budget. The original
two NPY files remain on the ground station, **184,320,128 bytes each**, with
SHA-256 hashes in the session metadata. The fire-uplink service remains paused
while this bench session continues and must be restored afterward.

[Capture settings, hashes and analysis](files/2026-10-23/iq-heartbeat-01-session.json) ·
[IHU replies and later fault status, hardware ID redacted](files/2026-10-23/iq-heartbeat-01-ihu.txt) ·
[Burst block-power data](files/2026-10-23/iq-heartbeat-01-power.csv) ·
[Preamble symbol measurements](files/2026-10-23/iq-heartbeat-01-preamble.csv) ·
[Plot reproduction script](files/2026-10-23/plot_iq_capture.py)

## October 23 — repeat capture and phase comparison

I repeated the conducted heartbeat with the same J9 → DC block →
20/10/6/3/2/1 dB pad chain → physical RXA connection. Between IQ captures I
switched off **only the 5 V supply**; the 3.3 V supply stayed on. Both rails
were back on before the second capture. This was a partial power interruption,
not a full board reboot: the COMMS boot ID remained unchanged. Receiver settings
and the reviewed runtime images were unchanged, and no MCU firmware was modified.

The assistant started another 120-second dual-channel IQ recording and enabled
IHU console debug output for timestamped CAN logging. The first logger reported
ready and then exited because its event writer passed the UTC field twice. The
pre-transmit liveness check caught that failure, so **no heartbeat was sent with
the failed logger**. Its files were retained. The corrected logger was started
and checked again while IQ recording continued; I then authorized exactly one
heartbeat. There were no automatic RF retries.

The IHU submitted request **19**, 38 bytes, and reported QUEUED followed by
RF_TX_COMPLETE with digest `74342ca7`. The normal DBPSK decoder recovered a
HEARTBEAT with outer RF sequence 19 and native sequence 15 on both channels.
The native CRC32 matched `74342ca7`; the outer CRC32 and native CRC16 both passed.
As before, the second channel is a weaker copy of the same RF event. Independently
saved full TX bytes are still unavailable, so the sender comparison remains a
length/digest match. No packet was forwarded or acknowledged over RF.

| Quantity | First IQ capture | Repeat IQ capture |
| --- | --- | --- |
| Completed RF attempts | 1 | 1 |
| IHU request / native digest | 18 / `4104665e` | 19 / `74342ca7` |
| Outer RF / native sequence | 18 / 14 | 19 / 15 |
| Normal DBPSK decode | Passed on both channels | Passed on both channels |
| Samples per channel | 23,040,000 | 23,040,000 |
| UHD errors / detected gaps / I/Q components ≥0.99 | 0 / 0 / 0 | 0 / 0 / 0 |
| Channel-0 burst interval, 10 ms power threshold | 68.28–68.97 s | 64.17–64.85 s |
| Channel-0 peak block power / median idle power | 45.96 dB | 45.96 dB |
| Normal decoder relative CFO, channel 0 | −7347.20 Hz | −7373.68 Hz |
| Known-preamble common frequency refinement | +0.756 Hz | +4.646 Hz |
| Refined relative CFO | −7346.44 Hz | −7369.03 Hz |
| Phase separation after common refinement | **134.14°** | **134.73°** |
| State-1 / state-0 mean amplitude ratio | 1.105 | 1.086 |
| Within-state phase standard deviations | 9.72° / 9.82° | 10.75° / 10.73° |
| IHU lifetime CAN TX-failure count | 3 → 4 | 4 → 4 |

The repeat's peak 10 ms digital power on channel 0 differed by only **+0.011 dB**
from the first capture. This is a relative receiver observation, not a calibrated
TX power comparison. The refined relative CFO shifted by about **−22.59 Hz**;
the two independent RF clocks were not calibrated, so this cannot be assigned
to transmitter drift alone.

### Is the phase separation still around 134 degrees?

**Yes, within this method's timing sensitivity.** Reprocessing the first capture
reproduced its published timing, variance metric, coarse phase separation,
common frequency refinement and final **134.1439°** result to floating-point
precision. Applying the same sequence of operations to the repeat yielded
**134.7273°**, a difference of **+0.5834°**.

![Measured preamble constellations and relative block power for both heartbeat captures](images/iq-heartbeat-repeat.svg)

Both measurements use 248 known preamble symbols, omit four at each end, and
average the central 8 of 40 samples per symbol. Timing is selected by normalized
within-state complex variance among CRC-valid frame alignments, after the normal
decoder's squared-IQ frequency estimate. One additional common linear phase slope
is then fitted across the preamble. The two complex state centers remain
independent; neither is forced to the ideal 180° alphabet. The plots use one
global rotation/scale per capture solely to align state 0 for viewing.

The repeat also shows a limitation of that ordering. Before the common frequency
refinement, its residual phase rotation spreads the points almost around a full
circle: the selected timing's raw state-center separation is 136.08°, with about
96° within-state phase spread. It is not a stable steady-state constellation at
that stage. Removing the fitted common +4.646 Hz slope produces the tighter clouds
shown above. The normal differential decoder already accepted the packet before
this offline refinement; the refinement was not needed to make its CRC pass.

As a sensitivity check, applying the same single common frequency refinement at
each CRC-valid timing gives separations of **134.14–135.62°** for the first capture
and **133.62–135.35°** for the repeat. Those ranges are timing sensitivity, not
confidence intervals. The sub-degree difference between the selected results is
smaller than that variation, so the defensible observation is a repeatable
**roughly 134–135°** phase alphabet. These are waveform estimates through this
receiver/filter path, not calibrated phase measurements directly at J9.

This repeats the largest departure from the paper's ideal antipodal transmitter.
It does not yet quantify the BER or noise-margin cost. Two decoded heartbeats are
a useful repeatability check, not the planned packet-success trial budget. Current
clock drive, installed transceiver firmware identity, circuit-stage responsibility,
and an independent receiver cross-check remain to be measured.

### CAN logging result and retained files

The corrected logger captured the heartbeat and more than two minutes afterward.
IHU status snapshots kept `tx_fail=4`, `tx_timeout=0`, TEC=0, REC=0 and RX overflow=0;
no new FRAME_TX_FAILED message or code-3 fault appeared. Thus the earlier CAN
failure **did not recur in this repeat**; its cause is still unresolved. Ten-second
status snapshots cannot exclude a short counter/register excursion between reads,
although the continuous debug stream covered the interval. Logging restored
`cli_debug=0` when it closed at 16:22:57.720 UTC. Neither the failure counters nor
the fault history was cleared.

Both new IQ originals remain unchanged on the ground station, 184,320,128 bytes
each, with SHA-256 recorded below. The failed logger and the earlier local analysis
draft were retained separately. The latter used a different variance normalization;
correcting it to reproduce the first measurement did not change the selected timing
or either final phase separation. Published derived files use the reproduced method.

[Repeat settings, hashes, comparison and timing candidates](files/2026-10-23/iq-heartbeat-02-session.json) ·
[Complete corrected IHU console log, hardware ID redacted](files/2026-10-23/iq-heartbeat-02-ihu.txt) ·
[Repeat block-power data](files/2026-10-23/iq-heartbeat-02-power.csv) ·
[Repeat preamble symbol measurements](files/2026-10-23/iq-heartbeat-02-preamble.csv) ·
[Offline analysis script](files/2026-10-23/analyze_iq_repeat.py) ·
[Comparison plot reproduction](files/2026-10-23/plot_iq_repeat.py)

## October 23 — Pluto independent receiver cross-check

The next check was whether a second receiver would see the same non-antipodal
phase states. I moved the complete DC-block/pad chain from LibreSDR RXA to
**Pluto RX** and connected Pluto by USB to the ground station. Both transceiver
rails were reported on at the start; the transmitter stayed idle until the
explicitly authorized heartbeat. No drive setting or MCU firmware was changed.

The unit identified as **PlutoSDR Rev. C, Z7010/AD9363A, firmware v0.37**.
The host lacked libiio, so `libiio0`, `libiio-utils` and `python3-libiio` version
0.26-2 were installed. A first broad attribute survey encountered an unreadable
attribute; targeted reads worked. This was a host-tool setup step, not a Pluto
firmware update. Pluto's DDS sources were disabled, TX attenuation set to
−89.75 dB and TX LO powered down; no TX buffer was created.

The RX setup requested 437 MHz, manual 0 dB gain, AGC off and 200 kHz analog
bandwidth. RX LO readback was 436,999,998 Hz, which is a register readback, not
an absolute-frequency calibration. The PHY ran at **2.304 Msample/s**, with the
advertised FPGA 8:1 RX decimation producing **288 ksample/s**. A five-second idle
check saved 1,440,000 complex samples without a reported read error or near-full-
scale component. The same numeric gain setting does not establish equal analog
gain or input calibration between Pluto and LibreSDR.

After that check, the assistant started a bounded 120-second IQ recording and
150-second IHU debug logger, verified both processes were running and the IHU had
no pending request, then issued exactly **one** heartbeat. Request **20** reported
QUEUED and RF_TX_COMPLETE, 38 bytes, digest `13049149`. There were no retries.

### Decode and phase comparison

The unchanged normal DBPSK decoder recovered **one HEARTBEAT**, outer RF sequence
**20**, native sequence **16**, with valid outer CRC32 and native CRC16. Recovered
length 38 and native CRC32 `13049149` match the IHU report. No diagnostic phase
threshold was substituted to obtain acceptance. Full independently saved TX
bytes remain unavailable; no RF acknowledgment or application forwarding occurred.

| Quantity | LibreSDR 1 | LibreSDR 2 | Pluto 1 |
| --- | --- | --- | --- |
| IHU request / native digest | 18 / `4104665e` | 19 / `74342ca7` | 20 / `13049149` |
| Outer RF / native sequence | 18 / 14 | 19 / 15 | 20 / 16 |
| Normal DBPSK decode and sender length/digest match | Passed | Passed | Passed |
| Recorded stream rate | 192 ksample/s | 192 ksample/s | 288 ksample/s |
| Recording duration / samples per channel | 120 s / 23,040,000 | 120 s / 23,040,000 | 120 s / 34,560,000 |
| Reported stream errors | 0 | 0 | 0 |
| Timestamp continuity check | No detected gaps | No detected gaps | Not available in this IIO stream |
| Normal decoder relative CFO | −7347.20 Hz | −7373.68 Hz | −3241.47 Hz |
| Additional common frequency refinement | +0.756 Hz | +4.646 Hz | +4.369 Hz |
| Refined relative CFO | −7346.44 Hz | −7369.03 Hz | −3237.10 Hz |
| Phase separation after refinement | **134.14°** | **134.73°** | **134.77°** |
| State-1 / state-0 mean amplitude ratio | 1.105 | 1.086 | 1.103 |
| Within-state phase spread | 9.72° / 9.82° | 10.75° / 10.73° | 7.89° / 7.96° |
| IHU lifetime CAN TX-failure count | 3 → 4 | 4 → 4 | 4 → 4 |

![Known preamble phase states through both LibreSDR captures and Pluto](images/iq-pluto-comparison.svg)

Pluto's primary result is **134.7692°**, just **0.0419°** from the second LibreSDR
capture and **0.6253°** from the first. These differences are smaller than the
method's timing sensitivity, so the useful conclusion remains **roughly 134–135°**,
not fractional-degree calibration. Pluto timing candidates that also decode the
same CRC-valid frame give **134.56–135.62°** after common frequency refinement.
These ranges are sensitivity checks, not confidence intervals.

To handle the different input rate, the Pluto excerpt was filtered with a
193-tap Hamming-windowed lowpass at 18 kHz and decimated 6:1 to 48 ksample/s.
Scaling from 129 taps at 192 ksample/s approximately preserves the first analysis
filter's duration. It does not make the receivers' native analog/FPGA filters
identical. From 48 ksample/s onward the procedure is unchanged: normal squared-IQ
CFO correction, 40 timing candidates with CRC-valid frame alignment, central
8 of 40 samples on 248 known preamble symbols, lowest normalized within-state
complex variance, then one common linear phase refinement with two unconstrained
state centers. No per-symbol phase rotation or enforced antipodal mapping is used.

As an offline filter check, **129 taps at 288 ksample/s** recovered the identical
packet and gave **134.7491°**, only **0.0201°** below the primary result. Both
filters' CSVs and timing candidates are retained. The pre-refinement Pluto
estimate was 135.66° with about 95° within-state phase spread; the common
+4.369 Hz refinement removes the residual rotation before the plotted comparison.
The normal differential decoder accepted the packet before this refinement.

Agreement through the independent receiver makes a **LibreSDR-only artifact less
likely** and strengthens the evidence that the received waveform is non-antipodal.
The common analysis method and passive path remain shared, and the responsible
transmitter stage has not been isolated. The paper's ideal 180° BPSK waveform is
still a reference model; these captures do not yet measure the resulting BER or
noise-margin penalty.

### Pluto measurement limits and CAN result

The Pluto burst's largest raw I/Q component was **26 counts out of nominal
2048 full scale**, only about **1.27%**, with zero components meeting the stated
0.99-full-scale clipping criterion. At fixed gain 0 dB, **76.98% of the 10 ms
blocks had exactly zero digital power**, making median idle power zero. An
idle-referenced digital SNR is therefore **unavailable**, not infinite. The small
ADC code excursion limits accuracy and should be improved in a later, separately
recorded gain check. The lower plotted phase spread is not proof that Pluto is a
better receiver, and raw digital power cannot be compared as calibrated RF power.

The burst occupies approximately **4.39–5.08 s** into the recording using an
explicit **20 dB below peak block-power** threshold. This is a different threshold
from the LibreSDR idle-referenced display. An initial analysis draft labelled all
nonzero blocks as above a zero-median noise threshold; that draft was retained
and corrected before publication. The correction did not change the decoded
packet, selected excerpt or phase result.

All **34,560,000** requested samples were saved, and refills reported no errors.
Unlike the UHD recordings, this libiio path supplies no per-sample timestamps and
no independently read FPGA overflow counter was collected. Thus the sample count
and successful reads do **not** establish gap-free continuity. The original NPY
is **138,240,128 bytes** and its SHA-256 was recomputed before analysis; full-rate
evidence and derived excerpts remain separate.

The IHU's corrected continuous log contains one heartbeat command. Status
snapshots kept TX failures at 4, TX timeouts at 0, TEC/REC at 0 and RX overflow at
0, with no new fault. Debug output returned to `cli_debug=0` when logging closed
at **16:40:37.500 UTC**. The original CAN failure remains unresolved. The ground
fire-uplink service remains paused while the bench session continues.

[Pluto settings, hashes, quantization limits and timing candidates](files/2026-10-23/iq-pluto-01-session.json) ·
[IHU console, hardware ID redacted](files/2026-10-23/iq-pluto-01-ihu.txt) ·
[Five-second block-power excerpt](files/2026-10-23/iq-pluto-01-power.csv) ·
[193-tap preamble measurements](files/2026-10-23/iq-pluto-01-preamble-193tap.csv) ·
[129-tap control measurements](files/2026-10-23/iq-pluto-01-preamble-129tap.csv) ·
[Offline Pluto analysis](files/2026-10-23/analyze_pluto_capture.py) ·
[Three-capture plot reproduction](files/2026-10-23/plot_pluto_comparison.py)

## October 23 — Pluto gain check at 20 dB

The first Pluto burst used only 26 raw ADC-format counts at its largest I/Q
component. The next question was whether the approximately 135° result would
persist with more digital signal. I authorized the assistant to run this check
through to results without asking for approval at each step. The RF wiring,
DC block, all six pads and both powered transceiver rails stayed as reported.

Only Pluto's **manual RX gain changed from 0 to 20 dB**, with readback confirmed.
The receiver kept the same 437 MHz requested tune, 200 kHz bandwidth, 2.304 Msample/s
PHY rate, 288 ksample/s stream and 193/129-tap offline filter comparisons. AGC
remained off. Pluto's TX DDS sources remained disabled, its TX LO powered down
and TX attenuation at −89.75 dB. No firmware or transmitter drive change was made.

For this targeted check the assistant recorded **30 seconds** of IQ, rather
than another 120-second idle-heavy record, and **45 seconds** of IHU debug logging.
Both processes were verified active and IHU pending counts zero before issuing
exactly **one heartbeat**. Request **21** reported QUEUED then RF_TX_COMPLETE,
38 bytes, digest `971c7052`. No automatic retry or additional RF test was needed.

### More ADC usage, same approximate phase alphabet

The unchanged normal DBPSK decoder recovered outer RF sequence **21**, native
HEARTBEAT sequence **17**, with valid outer CRC32 and native CRC16. Recovered
length/digest matched the IHU report. Both offline filters accepted the identical
packet. Full independent TX bytes were still unavailable; no packet forwarding
or RF acknowledgment occurred.

| Quantity | Pluto baseline, 0 dB gain | Pluto gain check, 20 dB gain |
| --- | --- | --- |
| Recording duration / samples | 120 s / 34,560,000 | 30 s / 8,640,000 |
| IHU request / native digest | 20 / `13049149` | 21 / `971c7052` |
| Normal decode and sender length/digest match | Passed | Passed |
| Peak absolute raw I/Q component | 26 counts | **233 counts** |
| Peak component / nominal full scale 2048 | 1.27% | **11.38%** |
| Components meeting the ≥0.99-full-scale criterion | 0 | 0 |
| Reported IIO read errors | 0 | 0 |
| 10 ms blocks with exactly zero power | 76.98% | **0%** |
| Primary 193-tap phase separation | 134.77° | **135.13°** |
| 129-tap control phase separation | 134.75° | **135.09°** |
| Refined state-amplitude ratio | 1.103 | 1.054 |
| Refined within-state phase spreads | 7.89° / 7.96° | 10.78° / 10.80° |
| Normal decoder relative CFO | −3241.47 Hz | −2563.41 Hz |
| Additional common frequency refinement | +4.369 Hz | +5.985 Hz |
| Refined relative CFO | −3237.10 Hz | −2557.42 Hz |
| IHU lifetime CAN TX-failure counter | 4 → 4 | 4 → 4 |

![Pluto preamble constellations at 0 and 20 dB gain, with raw ADC code usage](images/iq-pluto-gain-check.svg)

The primary phase estimate changed by **+0.3625°**, from 134.7692° to
135.1317°. The gain-check timing sensitivity is **134.18–135.47°**, larger than
that change. The shorter-filter control gives 135.0874°, only 0.0443° below the
primary result. The same known-preamble procedure and one common frequency
refinement were used; the plot does not force the state centers antipodal or
rotate individual symbols to target phases.

The peak 10 ms digital block power rose by **19.43 dB**, broadly consistent with
the requested 20 dB gain increase. This compares burst blocks, not full-record
RMS: the shorter gain-check record has a different transmit duty fraction.
It is a relative digital observation, not a calibrated receiver gain or RF power
measurement. The new median idle block power is nonzero, but the quantized idle
signal does not establish a calibrated noise density, SNR or Eb/N0.

Increasing ADC usage did **not** restore 180° phase separation. This supports
the conclusion that low digital amplitude alone was not responsible for the
baseline's roughly 135° alphabet. The four IQ results are now **134.14°, 134.73°,
134.77° and 135.13°**, through two receivers and two Pluto gains. Receiver and
common-analysis effects still limit absolute accuracy; the responsible transmitter
stage and the BER/noise-margin cost remain unmeasured. The larger phase spread
in this one higher-gain preamble is not evidence that more gain worsens BER.

The refined relative CFO changed by about **+679.68 Hz** between the sequential
Pluto captures, while tune readback stayed the same. Temperature and independent
clock accuracy were not controlled, so this cannot be assigned to gain or the
transmitter alone. The normal receiver removed bulk CFO before decoding, and the
known-preamble analysis removed one additional common slope. Future frequency
work needs an explicit time/temperature/reference record.

### Capture integrity and state left for the next test

All **8,640,000** requested samples were saved without a reported read error.
No raw component approached the stated near-full-scale criterion; this is not
an independent analog-linearity check. As in the first Pluto recording, the IIO
path has no per-sample timestamps and no independently collected FPGA overflow
counter, so gap-free continuity is not proven. The original NPY is **34,560,128
bytes**; its SHA-256 was recomputed before analysis and it remains unchanged.

The continuous IHU log records one heartbeat command and no new fault. TX-failure
count stayed 4, timeouts stayed 0 and TEC/REC and RX overflow were 0 at the saved
status snapshots. Debug output returned to its prior off setting when logging
closed at **16:54:50.511 UTC**. Pluto is left at **20 dB manual RX gain**, with
its TX path muted; RF wiring and transceiver power were not changed. The ground
fire-uplink service remains paused during this ongoing bench session.

[Gain setting, capture, hashes, phase candidates and comparison](files/2026-10-23/iq-pluto-gain20-01-session.json) ·
[IHU console, hardware ID redacted](files/2026-10-23/iq-pluto-gain20-01-ihu.txt) ·
[Five-second burst power excerpt](files/2026-10-23/iq-pluto-gain20-01-power.csv) ·
[193-tap preamble measurements](files/2026-10-23/iq-pluto-gain20-01-preamble-193tap.csv) ·
[129-tap control measurements](files/2026-10-23/iq-pluto-gain20-01-preamble-129tap.csv) ·
[Offline gain-check analysis](files/2026-10-23/analyze_pluto_gain_check.py) ·
[Gain-check plot reproduction](files/2026-10-23/plot_pluto_gain_check.py)

## October 23 — offline BER comparison with the paper

The phase checks established a baseline. The next step was to measure what the
roughly 135° waveform does in noise, while keeping that question separate from
frequency acquisition and the paper's ideal coherent receiver. This experiment
used **only saved IQ and generated signals**. No heartbeat, firmware update,
receiver configuration change or live decoder modification was performed.

The MATLAB `main.m` in the submitted archive matches the reviewed source exactly.
I reproduced the paper's AWGN references, preamble compensation and within-symbol
CFO-loss model in Python, with **Ns=8, normalized CFO=0.10, 64 data bits and
16/64-symbol pseudorandom preambles** where applicable. Independent NumPy RNG
streams and fixed budgets replace the MATLAB sequence/adaptive stopping; these
are new algorithm/equation reproductions, not copies of its old result CSVs.
Rayleigh fading and the full packet-length sweep remain future work.

### A diagnostic that does not throw away the errors

The normal receiver's CRC-valid output cannot be used as a BER denominator.
The new [offline diagnostic](files/2026-10-23/offline-ber/diagnostic.py) instead
returns decisions, error positions, timing, CFO, sync and CRC observations even
when sync/header/CRC fails. Tests deliberately corrupt preamble, sync and body
symbols to verify that failures survive. Incomplete or nonfinite IQ is an erasure,
not an invented correct bit.

For the hardware waveforms, the independently known truth is the **32-byte `55`
preamble**. Logical symbols 4–63 train the timing metric/state means, while bits
**68–251** provide **184 held-out scored bits**. Clean schedule/common CFO are
frozen from the earlier recordings for the first comparison. No noisy payload
error count, header or CRC selects alignment. The prior clean CFO calibration
used the known preamble, so this first mode is explicitly an oracle-conditioned
bound, not blind acquisition.

Native payload bytes reconstructed from a clean CRC-valid decode remain only a
**replay body reference**. They are not upgraded into independent saved TX bytes.
Body disagreement and scheduled frame CRC observations are retained separately
from the known-preamble BER.

### Noise calibration and budgets

The four derived excerpts are at **48 ksample/s**. Their observed preamble energy
per symbol, minus idle sample power, is normalized to one. New circular complex
white noise is inserted at this already filtered digital replay plane, **before
rectangular symbol integration**, with total complex variance `N0` and `N0/2`
per real dimension. Existing capture noise remains; only the additional variance
needed for the target is added. The largest original-noise correction is just
**5.38e-6 of the strongest target's noise variance**.

The frozen sweep uses mathematically equivalent matched-filter sufficient
statistics for the new white noise; a sample-domain test checks that projection.
The noisy synchronization pilot operates on the full sample-domain excerpts.
Neither experiment models noise before the original physical receive filters or
calibrates analog sensitivity, noise figure, RF Eb/N0 or range.

All sweeps use **−4 through 12 dB in 2 dB steps** and three independent RNG streams.
The frozen waveform curves score **6,000 × 184 = 1,104,000 bits per point**. The
paper compensation curves score **18,000 × 64 = 1,152,000 data bits per point**.
The synchronization pilot uses a smaller **150 trials / 27,600 known bits per
point**, labelled as a pilot. Those are new noise realizations of four fixed
recordings, not millions of new RF transmissions or independent hardware states.

### Waveform and detector cost

![Ideal and captured-waveform BER, with differential data decisions and coherent phase-state bounds kept separate](images/offline-waveform-ber.svg)

At the normalized replay **8 dB** point:

| Case | Errors / 1,104,000 scored bits | BER |
| --- | --- | --- |
| Ideal coherent BPSK, direct/phase bits | 215 | 0.00019475 |
| Ideal DBPSK, random data bits | 1,001 | 0.00090670 |
| Idealized 135° rectangular waveform, DBPSK | 17,635 | 0.01597373 |
| LibreSDR 1 capture, frozen DBPSK | 19,563 | 0.01772011 |
| LibreSDR 2 capture, frozen DBPSK | 19,472 | 0.01763768 |
| Pluto 0 dB capture, frozen DBPSK | 18,523 | 0.01677808 |
| Pluto 20 dB capture, frozen DBPSK | 18,997 | 0.01720743 |

The ideal cases agree with theory: at reliable-count points the largest relative
mismatch is **2.9%**, at most **2.06 trial-block standard errors**. The coherent
panel scores phase-state bits, not differentially decoded native data. Its
nearest-center receiver is a separate bound, not the deployed receiver.

Coarse log-BER interpolation on the 2 dB grid places captured-waveform DBPSK BER
`1e-3` at about **11.7–11.8 dB**, versus ideal DBPSK theory **7.93 dB**. That is
roughly **3.8–3.9 dB extra for this preamble and current detector**. The paper's
ideal coherent reference reaches that BER at **6.79 dB**. These are normalized
replay comparisons, not calibrated input-power/sensitivity claims.

The 135° model accounts for much of the extra loss, but **3.8 dB is not a universal
or irreducible cost of a 135° transmitter**. It describes this waveform interacting
with the adjacent-symbol real-product detector. The ideal two-state coherent
distance factor is `sin²(135°/2) ≈ 0.854`, about 0.69 dB, in that different receiver
model. Amplitude variation, residual phase behavior, filtering and detector choice
still matter; changing the receiver could change the result.

The bit classes explain why clean heartbeats had looked so good. At 8 dB, the
Pluto 20 dB replay has **592/552,000 errors on no-phase-change bits (0.107%)**, but
**18,405/552,000 on phase-change bits (3.334%)**. The 135° model has the same
asymmetry. The alternating preamble and a mostly zero-valued heartbeat body do
not have interchangeable BER, and adjacent differential errors can be correlated.
Do not predict heartbeat delivery by inserting this preamble BER into an IID
`(1-Pb)^Nb` formula.

### The paper's frequency-estimation result still matters

![Paper-model compensation and isolated within-symbol CFO-loss reproduction](images/offline-paper-model.svg)

In the paper-model reproduction at 8 dB, the 16-symbol known preamble gives
**52,326/1,152,000 errors (BER 0.04542)**, versus **226/1,152,000 (0.0001962)** for
64 symbols. That supports its frequency-estimation result under the paper's
ideal waveform assumptions. The finite 64-bit uncompensated case stays near
0.49 BER; the common 0.5 statement is a long-packet approximation here. The
Ns=8 integration-loss check also agrees with the discrete sinc expression,
including about 3.87 dB power loss at normalized residual offset 0.5 versus the
continuous approximation's 3.92 dB.

The real receiver estimates bulk CFO by squaring IQ, rather than stripping a
known pseudorandom preamble. The hardware's 256 transmitted preamble bits do not
make those estimators equivalent. Its raw kilohertz offset is removed before
symbol integration; it must not be substituted into the paper's residual-offset
curve as though it remained uncorrected.

### Noisy synchronization, with failed decisions retained

![Scheduled synchronization pilot with squared-IQ and a learned known-preamble CFO prototype](images/offline-synchronization.svg)

The pilot supplies the scheduled burst location, re-estimates CFO on each noisy
trial, and selects timing only from known training bits. It preserves the normal
squared-IQ frequency estimator but replaces CRC-based timing acceptance so all
BER decisions survive. Thus it is not a measurement of blind discovery or an
exact clone of the live CRC-search policy.

For Pluto 20 dB at 8 dB replay Eb/N0:

| Diagnostic case | Known preamble BER | Exact scheduled sync | Scheduled sync + body CRC32 |
| --- | --- | --- | --- |
| Squared-IQ CFO + training-only timing | 5,345 / 27,600 = **0.19366** | 46 / 150 | 3 / 150 |
| Learned 64-symbol hardware-template CFO | 491 / 27,600 = **0.01779** | 88 / 150 | 6 / 150 |

The second method adapts the paper's ML periodogram to clean learned hardware
state means. It also uses a shorter, scheduled 64-symbol observation. Prior clean
template/timing assistance and the changed observation window mean this is an
**offline prototype**, not a demonstrated blind/live replacement or an ablation
isolating each source of improvement. Under the same injected noise it approaches
the frozen waveform result of **0.01721**, separating a synchronization penalty
from the waveform/detector penalty. The small 3/150 and 6/150 frame counts do not
establish a reliable packet-success improvement; Wilson intervals are saved.
White noise was inserted after the original receive filters, so absolute pilot
acquisition thresholds need a pre-filter noise test before deployment conclusions.

### Reproducibility and limits

Ten behavioral tests pass, including CRC/sync failure retention, truth-window
isolation, invalid-IQ erasures and noise projection. All four clean captures pass
all three diagnostic CLI modes. The vectorized paper frequency estimator matches
the supplied scalar implementation exactly on 62 noisy signed-offset cases.
The frozen and paper count/interval CSVs were reproduced byte-for-byte with the
final estimator implementation. The plots are calculated from saved counts.

BER intervals use independent injected-noise **trial blocks**, allowing dependence
among adjacent bits; they are conditional on each fixed waveform. Sparse tails
are flagged, zero-error logarithmic points are omitted, and zero counts retain
conservative trial-based bounds in the CSVs. Sync/frame fractions include Wilson
intervals. These are not confidence intervals across temperatures, independent
hardware bursts or unknown payloads. Pluto timestamp continuity remains unverified.

[Methods, exact budgets, results and reproduction commands](files/2026-10-23/offline-ber/README.md) ·
[Diagnostic decoder](files/2026-10-23/offline-ber/diagnostic.py) ·
[Frozen waveform BER counts](files/2026-10-23/offline-ber/fast-summary.csv) ·
[Paper reproduction counts](files/2026-10-23/offline-ber/paper-summary.csv) ·
[Bit-class error counts](files/2026-10-23/offline-ber/transition-ber.csv) ·
[Input/source manifest](files/2026-10-23/offline-ber/manifest.json) ·
[Published-file provenance and validation](files/2026-10-23/offline-ber/publication.json)

## 2026-10-23 — held-out captures without timing or CFO supplied

I froze the learned waveform model from **libre01 only**, then searched the complete
four-second libre02, pluto00 and pluto20 excerpts. The receiver receives only IQ
and that fixed model: no capture-specific start, CFO or expected body. It searches
±12 kHz and integer sample timing, uses the unique sync word to resolve the repeating
0x55 preamble, and returns failed decisions without CRC gating. These are recordings
already examined in this investigation, so this is a retrospective capture holdout,
not prospective testing on new RF data. All work remained offline.

All three clean held-out captures acquire, decode and pass CRC, with zero errors
in **552 known preamble bits** and estimated CFO within **0.34 Hz** of the earlier
clean reference. The template therefore transfers between these recordings after
allowing unknown phase and amplitude; it no longer needs each test capture's clean
state means.

I also ran 30 trials per capture at each of 8 and 12 dB normalized replay Eb/N0,
randomizing delay, added CFO (±1.5 kHz), phase and gain without telling the receiver.
The 180 noisy trials keep acquisition and BER accounting separate:

| Capture | 8 dB correct start | 8 dB conditional preamble BER | 8 dB sync + CRC | 12 dB correct start | 12 dB sync + CRC |
| --- | --- | --- | --- | --- | --- |
| LibreSDR 02 | 26/30 | 88/4,784 = **1.84%** | 0/30 | 28/30 | 22/30 |
| Pluto, 0 dB gain | 30/30 | 88/5,520 = **1.59%** | 2/30 | 29/30 | 24/30 |
| Pluto, 20 dB gain | 28/30 | 71/5,152 = **1.38%** | 0/30 | 25/30 | 23/30 |

There are **14 wrong-start candidates** across the noisy trials and no
below-threshold misses. Wrong starts are thousands of samples away; they are
retained as acquisition failures and do not silently enter aligned BER. All
14 fail sync/CRC. The non-monotonic Pluto20 start counts and small trial budget
mean this is not a measured acquisition curve. Noise-only controls return no
candidate in 30 four-second windows, but their one-sided 95% upper bound is still
9.50% per window. This does not establish an operational false-alarm rate.

This connects directly to the paper: a preamble can estimate frequency across
captures without supplied CFO, but synchronization reliability remains separate
from the roughly 135° waveform/differential-detector penalty. Correctly acquired
8 dB trials still show percent-level BER. BER here is conditional on acquisition
of a known preamble; the initial periodic search may observe that region, so it
is not independent unknown-payload BER. Body comparisons remain clean-decode replay
comparisons, not independently recorded transmitted truth. Noise was added after
receive filtering; it is not calibrated analog sensitivity.

Five behavioral tests and independent recounts of every returned decision pass.
An initial numerical failure with zero-energy windows was fixed and the entire
budget rerun with the same template, threshold and seeds. No receiver parameters
were tuned to held-out errors. The bounded local search still has frame-boundary
and frequency ambiguities, so this remains an offline diagnostic prototype.

[Full method, limits and results](files/2026-10-23/offline-blind/README.md) ·
[Unassisted receiver](files/2026-10-23/offline-blind/receiver.py) ·
[All trial decisions and failures](files/2026-10-23/offline-blind/trials.jsonl) ·
[Counts](files/2026-10-23/offline-blind/summary.csv) ·
[Uncertainty intervals](files/2026-10-23/offline-blind/intervals.csv) ·
[Validation](files/2026-10-23/offline-blind/validation.json)

## 2026-10-23 — training-only revision to frame-start selection

The first unassisted receiver still selected the wrong frame start in 14/180 noisy
held-out trials. I revised its score using **libre01 only** for development. The
old score combined preamble and sync correlation phasors across a long gap; residual
CFO can rotate them against one another. The new score fits phase/amplitude
separately in the early preamble and unique sync, then requires both fields to
support the same candidate. This also changes normalization/weighting, so the
comparison tests the combined revision rather than isolating one cause.

On 60 noisy training replays, correct starts improve from 54/60 to 60/60, with
zero candidates in 30 training noise-only windows. Training packet counts are
mixed (8 dB: 2/30 → 1/30; 12 dB: 27/30 → 28/30). I selected the revision for start
acquisition, keeping the learned geometry, 0.04 threshold, coarse search and bit
detector fixed. Six behavioral tests pass. The source/model and development
results were hashed before running the held-out set, and those hashes still match.

The frozen revision then ran on the **same** 180 noisy held-out cases, with identical
IQ sources, noise seeds, nuisance transforms and scoring rules. This remains a
retrospective test on reused recordings, not new RF data. All work remained offline.

| Replay Eb/N0 | V1 correct start | V2 correct start | V1 sync + CRC | V2 sync + CRC |
| --- | --- | --- | --- | --- |
| 8 dB | 84/90 | **89/90** | 2/90 | 2/90 |
| 12 dB | 82/90 | **90/90** | 69/90 | **76/90** |
| Total | 166/180 | **179/180** | 71/180 | **78/180** |

![Paired acquisition and packet counts for the frozen revision](images/frame-start-v2.svg)

Thirteen previous wrong starts now acquire correctly, and the remaining one is
rejected below the unchanged threshold. V2 emits **zero wrong-start candidates**;
no previously correct start or valid frame regresses in this paired budget. The
one miss is libre02 at 8 dB, seed 73193, trial 2 (score 0.030579 < 0.04). It stays
in the acquisition denominator and supplies no aligned BER bits. The revision
was not retuned after seeing it. All three clean held-out frames still pass,
with zero errors in 552 known preamble bits. Noise-only controls remain 0/30;
that budget still permits a 9.50% one-sided upper bound per four-second window.

This improves frame-start selection without removing the waveform/detector noise
penalty identified in the paper comparison. Correctly acquired 8 dB preamble BER
remains 1.36–1.87%, and 8 dB packet success does not improve. BER is conditional on
acquisition of known data; noise remains injected after receive filtering, and
body truth remains a clean-decode reference. The test does not establish unknown
payload BER, continuous-stream reliability or RF sensitivity.

Every saved decision/count was independently recounted. Original IQ and all
published v1 decoder/result files retain their hashes. The result is a useful frozen offline
revision with **one retained miss**, not a completed live qualification.

[Method, training evidence and full results](files/2026-10-23/offline-start-v2/README.md) ·
[Frozen receiver](files/2026-10-23/offline-start-v2/receiver.py) ·
[Pre-evaluation selection record](files/2026-10-23/offline-start-v2/selection.json) ·
[Paired counts](files/2026-10-23/offline-start-v2/paired-summary.csv) ·
[All trial decisions](files/2026-10-23/offline-start-v2/trials.jsonl) ·
[Hash/count audit](files/2026-10-23/offline-start-v2/audit.json)

## 2026-10-23 — detector using the learned 135° geometry

The earlier BER comparison used a sign-of-correlation bit detector, which places
the change/no-change boundary at 90°. I tested a detector using the two complex
states learned from **libre01 only**: 134.0815° separation with amplitude ratio
1.06758. It compares each adjacent symbol pair with the four possible state pairs,
fitting an unknown common phase/gain for that pair, and returns whether the states
changed. This is a pairwise likelihood rule, not a full sequence decoder or a
phase-only ablation.

The **v2 acquisition code, model and threshold are unchanged**. V3 replaces only
the bit decisions after acquisition; timing, CFO and expected body are never
supplied to it. On training data at 8 dB, errors fall from 95/5,336 to 29/5,336;
at 12 dB they fall from 6/5,520 to zero observed. Acquisition is identical, ten
behavioral tests pass, and the source/model/dependency were frozen before the
held-out rerun. Selection used training preamble BER, not CRC or body-reference
errors. All work stayed offline.

The held-out run repeats the same IQ and noise cases. **Every input IQ hash and
acquisition output matches v2 exactly**: 179/180 noisy acquisitions, the same one
miss, zero wrong starts. The paired detector result is:

| Replay Eb/N0 | Shared known bits | V2 preamble errors | V3 preamble errors | V2 sync + CRC | V3 sync + CRC |
| --- | --- | --- | --- | --- | --- |
| 8 dB | 16,376 | 265 (**1.618%**) | 106 (**0.6473%**) | 2/90 | 6/90 |
| 12 dB | 16,560 | 13 | **0 observed** | 76/90 | 90/90 |

![Paired detector results and bit-class tradeoff at 8 dB](images/geometry-v3.svg)

At 8 dB this is **60% fewer preamble errors** on identical acquired samples.
The paired trial-block change is −0.971 percentage points (approximate 95%
interval −1.180 to −0.762), conditional on these fixed recordings. All three clean
held-out frames still pass with zero errors in 552 known bits. The 12 dB zero
count and 90/90 frames are finite-budget observations, not proof of zero BER.

The tradeoff matters: at 8 dB, changed-bit errors fall **254 → 29**, while false
changes on unchanged bits increase **11 → 77** (8,188 bits per class). Total valid
frames rise **78/180 → 96/180**, with 20 recoveries and **two regressions**. Both
regressions are Pluto00 at 8 dB and introduce 0→1 body differences against the
clean replay reference; one also has a sync error. They remain in the ledger.
A balanced preamble result does not guarantee the same gain on zero-heavy payloads.

This connects to the paper by showing that some of the earlier noise penalty
belongs to the bit detector's assumptions. Accounting for the actual geometry
improves BER without changing the transmitter or acquisition. It does not make
the physical link equivalent to ideal coherent BPSK or establish a universal dB
sensitivity gain. The result remains conditional known-preamble BER on reused
recordings with post-filter replay noise; independent full TX-body truth is still
unavailable. No detector was retuned against these held-out outcomes.

All original captures and v1/v2 source/results retain their hashes. Every saved
count, sync/CRC observation and baseline decision was checked independently.
The live receiver remains unchanged.

[Full method, training evidence and results](files/2026-10-23/offline-geometry-v3/README.md) ·
[Frozen detector](files/2026-10-23/offline-geometry-v3/receiver.py) ·
[Paired counts and BER intervals](files/2026-10-23/offline-geometry-v3/paired-summary.csv) ·
[Bit-class counts](files/2026-10-23/offline-geometry-v3/bit-class-summary.csv) ·
[Retained frame regressions](files/2026-10-23/offline-geometry-v3/frame-regressions.json) ·
[All trial decisions](files/2026-10-23/offline-geometry-v3/trials.jsonl) ·
[Pre-evaluation freeze](files/2026-10-23/offline-geometry-v3/selection.json)

## Current outcome and next session

The spectrum/phase checks now tie to the paper through controlled offline BER
comparisons. Ideal references reproduce theory. The sign detector has a large
penalty on the roughly 135° waveform; a detector using the learned geometry
reduces 8 dB known-preamble errors by 60% on the same acquired samples, while
increasing false changes and regressing two packets. A training-only acquisition
revision retains one miss and no emitted wrong starts in this reused test budget.
Limited capture diversity, payload truth and noise-plane assumptions still prevent
live qualification.

Next: test detector behavior on independently known varied payloads using training
data, keeping the baseline and the two regressions visible. Reserve **new captures
with independently saved transmitted payloads** for prospective evaluation of the
frozen receiver, with matched pre-filter noise and separate acquisition accounting.
Then validate a selected algorithm with bounded conducted RF trials. Record the
installed transmitter firmware/clock drive before any modulation changes, and
include time/temperature/reference information in frequency tests. BER under
fading/drifting CFO and calibrated analog sensitivity remain open. Keep original
captures and the existing hardware configuration as the baseline. The separate
CAN failure has not recurred in the three logged repeats; cause remains unresolved.
The investigation remains **In progress**. Restore the ground station's paused
fire-uplink service when the bench session ends.

Use the [session worksheet](files/session-template.md) and
[measurement table](files/measurements.csv) for subsequent runs. Keep original
data unchanged and distinguish proposed tests from performed steps.

[Sources and revisions](files/source-notes.md) ·
[Related bring-up](../003-ember-transceiver-bringup/README.md) ·
[Back to Lab Log](../../README.md)
