# 008 SDRB J14 doubler drive check

**Status:** In progress  
**Started:** 2026-10-25  
**Updated:** 2026-10-25

I wanted to take the DEMI transverter out of the measurement chain and check whether I could see a signal directly from SDRB's J14 output. I tried three TX gain settings with both amplifier supplies off, then repeated them with the driver supply on at 9 V. **None of the six steps produced a distinct tone near 5.184050 GHz.** All six two-second streams completed without reported stream or cleanup errors.

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

This does not locate the fault or establish the 10 GHz chain's performance. The doubler was tested below its specified band; actual driver current, fundamental power into the doubler, switch-control voltage and J14 output power remain unmeasured. The 10.3681 GHz output and DEMI downconversion are separate checks.

The next useful diagnostic is to check the fundamental through the driver-only Path B/J10 route at an analyzer-supported frequency, then return to an in-band doubler test with a suitable receiver. No additional RF run or power increase is implied by that proposal.

After the six runs, the original installed module was restored and its hash verified. MPM reported the radio unclaimed and no failed services were listed. AmpPwr1 was last reported on at 9 V; AmpPwr2 remained off. The investigation remains **In progress**.

[Back to SDRB RF_Out](../007-sdrb-rf-out/README.md) · [Equipment reference](../../equipment/README.md) · [Lab Log](../../README.md)
