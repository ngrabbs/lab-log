# 008 SDRB J14 doubler drive check

**Status:** In progress  
**Started:** 2026-10-25  
**Updated:** 2026-10-25

I wanted to take the DEMI transverter out of the measurement chain and check whether I could see a signal directly from SDRB's J14 output. I tried three TX gain settings with both amplifier supplies off, then repeated them with the driver supply on at 9 V. **None of the six steps produced a distinct tone near 5.184050 GHz.** All six two-second streams completed without reported stream or cleanup errors.

A subsequent **J10 fundamental measurement detected 5.184050 GHz at about −69.2 dBm with 20.3 dB contrast**, using 10 dB analyzer attenuation and the same gain 60/amplitude 0.1. See the J10 follow-up below.

These are exploratory measurements below the doubler's specified frequency range. The readings near the noise floor are not calibrated SDRB output-power measurements.

This is a separate part of the [SDRB RF_Out investigation](../007-sdrb-rf-out/README.md).

## Correcting the connection

On October 25 I identified a wiring mistake in the earlier October 24 tests: the cable had been on **Jx1, marked Path C**, rather than **J14, marked X2_RF_Out**. Jx1 connects to the unused branch of output switch U1; it is not the doubler output. Those earlier nondetections did not measure the intended J14 output.

For this investigation I moved the cable to J14. The initial direct measurement used:

`SDRB J14 → DC block → tinySA Ultra RF input`

The DEMI was bypassed and **no external attenuation pad was installed**. I retained the tinySA's 31 dB internal attenuation, with its LNA off. These are separate settings: removing the external pad did not remove the analyzer's internal attenuation.

## What the power controls mean

The installed native SDRB control uses a positive TX gain setting from **0 to 89.75 dB**. The AD9361 attenuation control has **0.25 dB increments**:

`nominal native TX attenuation = 89.75 − SDRB TX gain`

Gain 0 therefore means maximum attenuation; gain 89.75 means minimum attenuation. These numbers are **not output dBm**. Digital amplitude is another control: amplitude 0.1 is −20 dB relative to amplitude 1, and amplitude 0.01 is −40 dB. The gain of the driver stages, filter and switch losses, doubler behavior, cable loss and frequency all affect the level eventually reaching the analyzer.

The [AD9361 reference manual](https://www.analog.com/media/en/technical-documentation/user-guides/ad9361.pdf?isDownload=true) describes the attenuation range and resolution. This run checked only gain 0, 30 and 60, at amplitude 0.1; it did not characterize the full range.

AmpPwr1 powers the two PHA-83W+ driver stages. AmpPwr2 powers a separate final amplifier in Path A. **AmpPwr2 stayed off in every step.** The second sweep compares the driver supply on/off, not the separate final PA on/off.

## Frequency choice and its limitation

To bring the nominal doubled output within the tinySA's Ultra-mode range, I used:

| Parameter | Setting |
| --- | --- |
| Requested TX LO | 2,592,000,000 Hz |
| Reported TX LO, all six runs | 2,591,999,998.092648 Hz |
| Complex tone offset | +25,000 Hz |
| Nominal fundamental | 2,592,025,000 Hz |
| Nominal doubled output / analyzer marker | **5,184,050,000 Hz** |
| TX bank and route | High-pass / temporary Path C to J14 |
| Physical TX selector | UHD channel 1 |
| Sample rate / frame size | 2.304 MS/s / 8,000 bytes |
| Digital amplitude / requested duration | 0.1 / 2 seconds |
| External attenuation / gain correction | 0 dB / 0 dB |
| tinySA configuration | Ultra on; internal attenuation 31 dB; LNA off |
| Numeric scan | 5.183550–5.184550 GHz, 101 points, 10 kHz spacing |
| RBW | 10 kHz |
| LCD | 10 dB/div; reference −20 dBm; marker 5.184050 GHz |

The CY2-283+ is specified for **3.5–14 GHz input and 7–28 GHz output**, with +12 to +18 dBm drive. This test's 2.592025 GHz fundamental and 5.184050 GHz nominal output are below that band. A visible response would be useful, but **no response here does not establish that the doubler is faulty**. Actual drive at the doubler input was not measured.

Sources: [CY2-283+ datasheet](https://www.minicircuits.com/pdfs/CY2-283%2B.pdf), [tinySA specifications](https://tinysa.org/wiki/pmwiki.php?n=TinySA4.Specification).

## Procedure and controls

I ran the lowest gain first and checked each result before advancing. The initial three steps used both supplies off. After that sweep finished, I powered only AmpPwr1 at 9 V and repeated the same settings. Supply voltage/state were owner-reported; driver current was not recorded.

For each step I saved a numeric scan and a real LCD capture before the tone, during the tone, and after it stopped. A numeric scan and an LCD sweep are **separate sweeps**, so their instantaneous levels can differ. The active LCD was paused during the transmitting window; transferring its frozen pixels could finish after the tone stopped. Active freezes were verified within 1.8 seconds of the received stream-start marker. These are host timing observations, not RF timing calibration.

The instrument displays **REDUCED LINEARITY** on these captures. Its absolute calibration was not independently checked. Values below are the analyzer's indicated input dBm, not values with another 31 dB added. Cable and DC-block losses are uncorrected.

I used a measured full-band peak of −10 dBm as an escalation stop, kept the LNA off and retained the analyzer's internal attenuation. No measured peak approached that stop. The tinySA's published short-term input limit with 30 dB internal attenuation is +20 dBm; that is a damage limit, not a measurement target. No maximum-gain or calibrated-power qualification is implied by this sequence.

One initial analyzer-only preflight stopped because its expected frequency grid still contained an old upper bound. **No source stream started in that attempt.** I corrected the parser and checked it against the original capture, missing-bin, wrong-frequency and nonfinite-data cases before proceeding. The [aborted record](files/pre-rf-grid-validation-abort.json) is retained. The temporary module passed 58 simulated-hardware tests on host and SDRB; four analyzer-parser tests passed on host and measurement computer. Those tests do not validate RF hardware.

The base image remained `0.1.0-dev.4-rc.3`. A RAM-only `x2-c-bench-20261025-r6` option restricted the route to a 2.592 GHz LO within ±10 Hz and TX gain settings 0, 30 or 60. Initialization and cleanup retained gain zero. The installed demonstration's timing and stream-error accounting were preserved. The original persistent module and boot files were not replaced.

## Settings and results

| Step | AmpPwr1 | TX gain requested/read back | Native attenuation (dB) | Amplitude | Nominal output (GHz) | Actual duration (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| S1 | Both OFF | 0 / 0 | 89.75 | 0.1 | 5.184050 | 2.001389 |
| S2 | Both OFF | 30 / 30 | 59.75 | 0.1 | 5.184050 | 2.000755 |
| S3 | Both OFF | 60 / 60 | 29.75 | 0.1 | 5.184050 | 2.001237 |
| S4 | AmpPwr1 9 V | 0 / 0 | 89.75 | 0.1 | 5.184050 | 2.000750 |
| S5 | AmpPwr1 9 V | 30 / 30 | 59.75 | 0.1 | 5.184050 | 2.001092 |
| S6 | AmpPwr1 9 V | 60 / 60 | 29.75 | 0.1 | 5.184050 | 2.000789 |

AmpPwr2 was OFF and the expected output frequency was 5.184050 GHz in every row. "Native attenuation" describes the RFIC control, not the entire board or the resulting doubled signal.

The following values are the largest numeric readings within **±10 kHz of 5.184050 GHz**. With no distinct tone, they represent local noise-window peaks, not measured signal output powers. Contrast is `on − max(before, after)`; negative values describe noise variation.

| Step | Before (dBm) | Tone on (dBm) | After (dBm) | Rise (dB) | Distinct tone | Active screen |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| S1 | -69.75 | -70.41 | -71.75 | -0.66 | No | [LCD](images/amps-off-gain-0-active.png) |
| S2 | -69.25 | -71.25 | -69.91 | -2.00 | No | [LCD](images/amps-off-gain-30-active.png) |
| S3 | -65.69 | -71.69 | -68.84 | -6.00 | No | [LCD](images/amps-off-gain-60-active.png) |
| S4 | -71.19 | -70.34 | -68.84 | -1.50 | No | [LCD](images/drivers-on-gain-0-active.png) |
| S5 | -68.69 | -69.84 | -69.34 | -1.16 | No | [LCD](images/drivers-on-gain-30-active.png) |
| S6 | -67.69 | -70.84 | -66.34 | -4.50 | No | [LCD](images/drivers-on-gain-60-active.png) |

The predeclared detection candidate was a rise of at least 10 dB in that target window during the verified active interval. No step met it. All six reported actual TX gain settings matched their requests, all six streams completed, and no stream, decode or cleanup errors were reported. A benign post-stop burst acknowledgement was retained for each run.

[Complete CSV](files/measurements.csv) · [JSON summary](files/measurements.json) · [Configuration and module identities](files/test-configuration.json)

## Actual tinySA screens

These are unmodified 480 × 320 LCD pixel captures, not plots reconstructed from numeric data. Each step includes a before, active and after image. The per-screen JSON files include hashes of the PNG and original RGB565 payload, freeze times and capture timing. Original payloads and complete private bench records remain archived separately; public measurement JSON omits local result paths and connection arguments.

### S1: Both OFF, gain 0

![S1 Before, J14 direct measurement](images/amps-off-gain-0-before.png)

Before. [Numeric scan](files/amps-off-gain-0-before.txt) · [LCD metadata](files/amps-off-gain-0-before-screen.json)

![S1 Tone on — frozen during the two-second stream, J14 direct measurement](images/amps-off-gain-0-active.png)

Tone on — frozen during the two-second stream. [Numeric scan](files/amps-off-gain-0-active.txt) · [LCD metadata](files/amps-off-gain-0-active-screen.json)

![S1 After, J14 direct measurement](images/amps-off-gain-0-after.png)

After. [Numeric scan](files/amps-off-gain-0-after.txt) · [LCD metadata](files/amps-off-gain-0-after-screen.json)

[Step measurement record](files/amps-off-gain-0-measurement.json).

### S2: Both OFF, gain 30

![S2 Before, J14 direct measurement](images/amps-off-gain-30-before.png)

Before. [Numeric scan](files/amps-off-gain-30-before.txt) · [LCD metadata](files/amps-off-gain-30-before-screen.json)

![S2 Tone on — frozen during the two-second stream, J14 direct measurement](images/amps-off-gain-30-active.png)

Tone on — frozen during the two-second stream. [Numeric scan](files/amps-off-gain-30-active.txt) · [LCD metadata](files/amps-off-gain-30-active-screen.json)

![S2 After, J14 direct measurement](images/amps-off-gain-30-after.png)

After. [Numeric scan](files/amps-off-gain-30-after.txt) · [LCD metadata](files/amps-off-gain-30-after-screen.json)

[Step measurement record](files/amps-off-gain-30-measurement.json).

### S3: Both OFF, gain 60

![S3 Before, J14 direct measurement](images/amps-off-gain-60-before.png)

Before. [Numeric scan](files/amps-off-gain-60-before.txt) · [LCD metadata](files/amps-off-gain-60-before-screen.json)

![S3 Tone on — frozen during the two-second stream, J14 direct measurement](images/amps-off-gain-60-active.png)

Tone on — frozen during the two-second stream. [Numeric scan](files/amps-off-gain-60-active.txt) · [LCD metadata](files/amps-off-gain-60-active-screen.json)

![S3 After, J14 direct measurement](images/amps-off-gain-60-after.png)

After. [Numeric scan](files/amps-off-gain-60-after.txt) · [LCD metadata](files/amps-off-gain-60-after-screen.json)

[Step measurement record](files/amps-off-gain-60-measurement.json).

### S4: AmpPwr1 9 V, gain 0

![S4 Before, J14 direct measurement](images/drivers-on-gain-0-before.png)

Before. [Numeric scan](files/drivers-on-gain-0-before.txt) · [LCD metadata](files/drivers-on-gain-0-before-screen.json)

![S4 Tone on — frozen during the two-second stream, J14 direct measurement](images/drivers-on-gain-0-active.png)

Tone on — frozen during the two-second stream. [Numeric scan](files/drivers-on-gain-0-active.txt) · [LCD metadata](files/drivers-on-gain-0-active-screen.json)

![S4 After, J14 direct measurement](images/drivers-on-gain-0-after.png)

After. [Numeric scan](files/drivers-on-gain-0-after.txt) · [LCD metadata](files/drivers-on-gain-0-after-screen.json)

[Step measurement record](files/drivers-on-gain-0-measurement.json).

### S5: AmpPwr1 9 V, gain 30

![S5 Before, J14 direct measurement](images/drivers-on-gain-30-before.png)

Before. [Numeric scan](files/drivers-on-gain-30-before.txt) · [LCD metadata](files/drivers-on-gain-30-before-screen.json)

![S5 Tone on — frozen during the two-second stream, J14 direct measurement](images/drivers-on-gain-30-active.png)

Tone on — frozen during the two-second stream. [Numeric scan](files/drivers-on-gain-30-active.txt) · [LCD metadata](files/drivers-on-gain-30-active-screen.json)

![S5 After, J14 direct measurement](images/drivers-on-gain-30-after.png)

After. [Numeric scan](files/drivers-on-gain-30-after.txt) · [LCD metadata](files/drivers-on-gain-30-after-screen.json)

[Step measurement record](files/drivers-on-gain-30-measurement.json).

### S6: AmpPwr1 9 V, gain 60

![S6 Before, J14 direct measurement](images/drivers-on-gain-60-before.png)

Before. [Numeric scan](files/drivers-on-gain-60-before.txt) · [LCD metadata](files/drivers-on-gain-60-before-screen.json)

![S6 Tone on — frozen during the two-second stream, J14 direct measurement](images/drivers-on-gain-60-active.png)

Tone on — frozen during the two-second stream. [Numeric scan](files/drivers-on-gain-60-active.txt) · [LCD metadata](files/drivers-on-gain-60-active-screen.json)

![S6 After, J14 direct measurement](images/drivers-on-gain-60-after.png)

After. [Numeric scan](files/drivers-on-gain-60-after.txt) · [LCD metadata](files/drivers-on-gain-60-after-screen.json)

[Step measurement record](files/drivers-on-gain-60-measurement.json).

## Current outcome and next check

The commanded gain steps and finite source streams worked, and the actual analyzer screens and scans were saved. This direct, no-external-pad check did **not** produce a distinct expected doubled tone at any tested gain, with the driver supply either off or on at 9 V.

This does not locate the fault or establish the 10 GHz chain's performance. The doubler was tested below its specified band; actual driver current, fundamental power into the doubler and J14 output power remain unmeasured. Path C control voltages were subsequently checked as recorded below. The 10.3681 GHz output and DEMI downconversion are separate checks.

The next useful diagnostic is to check the fundamental through the driver-only Path B/J10 route at an analyzer-supported frequency, then return to an in-band doubler test with a suitable receiver. No additional RF run or power increase is implied by that proposal.

After the six runs, the original installed module was restored and its hash verified. MPM reported the radio unclaimed and no failed services were listed. AmpPwr1 was last reported on at 9 V; AmpPwr2 remained off. The investigation remains **In progress**.

## Datasheet and route review — October 25, 2026

This is a read-only review and a proposed diagnostic sequence. No additional RF run, KiCad edit or component replacement was performed.

The live KiCad PCB pad queries show U12 pin 3 and IC3 pin 5 on `Xmit Path C`, and IC3 pin 11 and J14 center pad 1 on the same output net. Routed segments are present between those endpoints. This supports the intended connection, but does not verify solder joints, RF impedance, or continuity on the assembled board.

`TX-B → U37/U45 drivers → U13 → U12 → IC3 → J14`

Path B instead leaves U12 through J2 and passes through U1 to J10. Path C's doubled output bypasses U1; the 10 GHz signal does not pass through either 6 GHz RF switch.

The [Skyworks truth table](https://www.skyworksinc.com/-/media/SkyWorks/Documents/Products/2201-2300/SKY13588_460LF_203512D.pdf) requires:

| State | U12 V1, pin 4 | U12 V2, pin 5 | Selected branch |
| --- | --- | --- | --- |
| Shutdown | low | low | None |
| Path B | high | low | J2, toward J10 |
| Path C | high | high | J3, toward IC3 |

The reviewed FPGA uses low-or-release outputs with external 1.8 V pull-ups. Measure **R92 pad 1 for V1 and R91 pad 1 for V2**, not the resistors' supply-side pad 2. Expect approximately 1.8/1.8 V during a held Path C selection, approximately 1.8/0 V during Path B, and near 0/0 V in shutdown. Verify U12's 3.3 V supply and the 1.8 V pull-up rail too.

The temporary module requested state 3 for Path C. That is command/software evidence, not physical voltage evidence. The reviewed FPGA source ties the processor GPIO input feedback low; a GPIO readback alone cannot establish the voltage at the switch. At that review point no R91/R92 voltage measurements had been recorded; the subsequent held-state readings below agree with Path C. The temporary module was removed after testing, so the restored idle state should not be mistaken for an active Path C selection.

[CY2-283+ datasheet](https://www.minicircuits.com/pdfs/CY2-283%2B.pdf) limits: input 3.5–14 GHz; output 7–28 GHz; drive +12 to +18 dBm; absolute maximum RF input +21 dBm. The recent lower-frequency test was outside specification; 5.184050 → 10.368100 GHz is in band. +12/+18/+21 dBm correspond to approximately 16/63/126 mW, leaving only 3 dB from the upper drive point to the damage limit.

IC3 has no DC supply/enable pin. AmpPwr1 supplies its preceding drivers; excessive RF from those drivers is the relevant overdrive mechanism. An attenuator after J14 protects a receiver, not IC3's input. Gain settings and supply voltage alone do not establish RF power at IC3.

Entry 007's historical 5.8001 GHz measurement was −71.5 dBm after a nominal 20 dB pad, or roughly −51.5 dBm before that pad if its nominal loss is added. This is uncalibrated and from a different frequency/configuration, not an IC3 input measurement. It illustrates why detecting RF_Out does not establish adequate doubler drive. Recheck the current setup at the actual intended fundamental before extrapolating earlier levels.

One pin-assignment detail needs manufacturer clarification: the datasheet labels pads 1, 2, 3, 7, 8 and 9 “no connections,” while the live layout assigns them to ground. This may be harmless if genuinely internally unconnected. It is not a demonstrated fault or a reason to rework the board without further evidence.

Proposed order, with each step recorded before proceeding:

1. **Verify selection electrically (subsequently completed below).** Use a deliberate low-drive route-hold diagnostic so a meter can read R92/R91 during B and C selection. Start with the driver supply off. Confirm the control states, supply rails and software mapping without relying on a two-second LCD or GPIO readback.
2. **Check assembly with power off.** Verify same-net continuity U12 pin 3 to IC3 pin 5, and IC3 pin 11 to J14 center; inspect the actual connector launch and ground/paddle joints. Resistance from an RF port to ground alone is not a conclusive failure test.
3. **Measure current fundamental drive (single-setting J10 check subsequently completed below).** Reproduce Path B/J10 detection at 5.184050 GHz on the current image, record actual AmpPwr1 voltage/current and gain/amplitude, and establish a measured level versus control setting. J10 is a first surrogate; its extra switch and launch losses mean it is not exactly IC3 input power.
4. **Establish a bounded in-band IC3 input.** Use suitable 50 ohm RF access and measured loss/uncertainty to establish the power reaching IC3 pin 5. Start at the lower specified drive point, +12 dBm, rather than blindly increasing software gain or using +21 dBm as a target. Typical conversion loss is around 13 dB, so an output near −1 dBm would be an order-of-magnitude expectation under the manufacturer's matched test conditions, not a board guarantee.
5. **Validate the 10 GHz receive path and test doubling.** Confirm the DEMI's LO/receive configuration and sensitivity with an independent reference where available. Verify the output connector, cable and DC block are suitable at 10.368 GHz; the previously inventoried 6 GHz-rated block does not establish 10 GHz performance. Restore appropriate receiver protection for a potentially much stronger in-band doubled output. With verified Path C selection and measured drive, look for on/off contrast at 144.100 MHz if the DEMI LO is 10.224 GHz. A second planned tone offset +10 kHz higher should move the doubled RF and the uninverted IF by +20 kHz; choose scan resolution that can resolve that shift.

There is presently **no evidence sufficient to declare IC3 damaged**. A useful failure diagnosis requires known in-band input power at IC3, verified switching and assembly, and a working output measurement chain. Grossly missing conversion under those conditions makes the IC or its assembly suspect; an independent component test or known-good substitution can then distinguish them.

## Path C control-voltage check — October 25, 2026

The owner measured the switch-connected pad 1 of each pull-up resistor during a dedicated GPIO-only Path C hold:

| Point | Signal | Owner-reported reading | Expected Path C state |
| --- | --- | ---: | --- |
| R92 pad 1 | U12 V1 | **1.8 V** | High |
| R91 pad 1 | U12 V2 | **1.8 V** | High |

The hold service was independently observed active when the readings were reported. The AD9361 was held in reset throughout; no RFIC initialization, tuning or sample stream was performed. MPM was stopped while the diagnostic exclusively owned the GPIO controls. These are manual meter readings reported by the owner, not automated GPIO voltage readbacks.

The owner also confirmed that all switching circuits had already been tested and read correctly. Individual values for those earlier checks were not supplied here and have not been invented. **Switch-control verification is complete; repeating it is not the next diagnostic.**

The next focus is the actual fundamental RF drive and in-band doubling. This check closes the outstanding Path C control-voltage question without changing the earlier RF measurements.

The diagnostic hold was released after measurement. Cleanup returned the controls to their inactive state and restarted MPM without errors; the radio was unclaimed and no failed services were listed. No new RF tone was sent.

## J10 fundamental measurement — October 25, 2026

With the switching checks complete, I moved the cable to **J10/RF_Out** to measure the fundamental before attempting further doubler tests:

`J10 → DC block → tinySA input`

No external pad was installed. AmpPwr1 remained at 9 V and AmpPwr2 stayed off, as owner-confirmed. This used driver-only **Path B / high-pass**, not J14 and not the separate final PA.

Both runs used requested LO **5.184000 GHz**, complex tone **+50 kHz**, expected fundamental **5.184050 GHz**, TX gain **60**, digital amplitude **0.1**, channel 1, 2.304 MS/s, 8,000-byte frames and a two-second duration. The reported gain was 60.0 and reported LO was 5,183,999,996.185296 Hz in both runs. The LO value is software readback, not independent RF frequency calibration.

The first run retained 31 dB analyzer attenuation. It did not give a clear target-window detection. All peaks were below −25 dBm, so I reduced **only the analyzer attenuation to 10 dB** and repeated the same source settings. No TX gain or amplitude increase occurred.

The analyzer remained in Ultra mode with LNA off, 10 kHz RBW, zero external correction and a 5.183550–5.184550 GHz / 101-point scan. Numeric values are peaks within ±10 kHz of the nominal tone; contrast is `on − max(before, after)`.

| Analyzer internal attenuation | Before (dBm) | Tone on (dBm) | After (dBm) | Rise (dB) | Duration (s) | Detection |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 31 dB | -71.03 | **-67.69** | -71.53 | +3.34 | 2.001208 | Not clear |
| 10 dB | -90.56 | **-69.22** | -89.56 | +20.34 | 2.000740 | Clear |

**The 10 dB setting clearly detected the fundamental:** the strongest active numeric bin was **5.184050 GHz at −69.22 dBm**, with **20.34 dB** off/on/off contrast. The fixed LCD marker on its separate active sweep read approximately **−70.1 dBm**. The 31 dB run's fixed LCD marker read approximately −72.5 dBm; its noise-window numeric peak is not a reliable isolated signal-power measurement.

These are indicated levels at the analyzer input. **Do not add the internal 10 or 31 dB attenuation to them.** There is no external pad correction; cable/DC-block losses and absolute calibration remain unqualified. The display still shows REDUCED LINEARITY. Improving analyzer sensitivity established detection without increasing source power.

Both streams completed with no reported stream, decode or cleanup errors. Each retained one benign post-stop burst acknowledgement. The numeric scans and actual active LCD freezes were verified inside the source windows; the LCD freezes occurred about 1.72 seconds after the received start markers. Each PNG is an unmodified device pixel capture; the numeric and LCD sweeps are separate observations.

The installed rc.3 native Path B/high-pass support was used. A RAM-only adapter changed the installed demo's device arguments and supplied fixed source parameters; it preserved the original demo's timing and error accounting. Twelve adapter/parser tests passed on host and SDRB ARM. No installed module, application or FPGA replacement was needed, and final hashes remained unchanged. The radio returned unclaimed with no failed services.

This confirms a detectable fundamental through the current J10 path at the intended frequency. It does **not** measure IC3 pin 5 directly: the J10 path includes an extra switch/launch, and the cable/DC-block loss is uncorrected. The indicated J10 level at this setting is very low relative to the doubler's specified drive. Actual driver bias/current, RF level progression through the chain, and a bounded IC3 input-power measurement are the next focus. No higher TX setting or 10 GHz run was performed here.

[CSV](files/j10-fundamental.csv) · [JSON summary](files/j10-fundamental.json) · [Fixed configuration](files/j10-test-configuration.json)

### J10, analyzer attenuation 31 dB

![J10 at 5.184050 GHz, 31 dB analyzer attenuation, before](images/j10-att31-before.png)

Before. [Numeric scan](files/j10-att31-before.txt) · [LCD metadata](files/j10-att31-before-screen.json)

![J10 at 5.184050 GHz, 31 dB analyzer attenuation, active](images/j10-att31-active.png)

Tone on, frozen during the source window. [Numeric scan](files/j10-att31-active.txt) · [LCD metadata](files/j10-att31-active-screen.json)

![J10 at 5.184050 GHz, 31 dB analyzer attenuation, after](images/j10-att31-after.png)

After. [Numeric scan](files/j10-att31-after.txt) · [LCD metadata](files/j10-att31-after-screen.json)

[Run record](files/j10-att31-measurement.json).

### J10, analyzer attenuation 10 dB

![J10 at 5.184050 GHz, 10 dB analyzer attenuation, before](images/j10-att10-before.png)

Before. [Numeric scan](files/j10-att10-before.txt) · [LCD metadata](files/j10-att10-before-screen.json)

![J10 at 5.184050 GHz, 10 dB analyzer attenuation, active](images/j10-att10-active.png)

Tone on, frozen during the source window. [Numeric scan](files/j10-att10-active.txt) · [LCD metadata](files/j10-att10-active-screen.json)

![J10 at 5.184050 GHz, 10 dB analyzer attenuation, after](images/j10-att10-after.png)

After. [Numeric scan](files/j10-att10-after.txt) · [LCD metadata](files/j10-att10-after-screen.json)

[Run record](files/j10-att10-measurement.json).

[Back to SDRB RF_Out](../007-sdrb-rf-out/README.md) · [Equipment reference](../../equipment/README.md) · [Lab Log](../../README.md)
