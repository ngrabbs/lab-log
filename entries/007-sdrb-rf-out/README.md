# 007 SDRB RF_Out check

**Status:** In progress  
**Started / updated:** 2026-10-20

Check the signal at **J10/RF_Out** using driver-only Path B, with the final PA off.

## Setup

`SDRB J10/RF_Out → DC block → 30 dB / 2 W pad → 10 dB / 2 W pad → tinySA Ultra`

- Main power and AmpPwr1 share **9.0 V**, current limit **0.7 A**. AmpPwr2 disconnected. Startup: **0.567 A, CV**; no visible supply change during the first checks, around **0.570 A** afterward.
- Native UHD channel 1, LO **438 MHz** (145 MHz for the follow-up below), complex tone **+100 kHz**, amplitude **0.1**, nominal **2.304 MS/s**. Each transmission lasts **8 seconds**.
- tinySA Ultra: **30 dB internal attenuation**, LNA off, **3 kHz RBW**, external correction **0 dB**. Scans: LO to LO +200 kHz, 201 points. Firmware `tinySA4_v1.4-156-g4eb315d`; no fresh calibration.
- Software: **0.1.0-dev.3**, with temporary RAM-only MPM changes from `0c8e7f744023b649bec167de9afc3b41fb57b7a3` and explicit `sdrb_tx_path=rf_out_b`. Original card files unchanged; FPGA PA enable remains low.

An initial silent boot was traced to a disturbed boot jumper. Restoring the documented SD-boot straps allowed Linux to boot.

## Results

Levels are measured **after the external 40 dB pads**. Off-state values are the strongest bin within ±5 kHz of 438.1 MHz; those bins need not match the tone bin.

| TX gain | Before | Tone on | After | Observation |
|---|---:|---:|---:|---|
| 30 dB | −82.4 dBm | −81.9 dBm | −81.9 dBm | Indistinguishable from background |
| 60 dB | −83.9 dBm | **−62.9 dBm at 438.100 MHz** | −82.4 dBm | Clear off/on/off contrast |
| 60 dB, repeat | −80.8 dBm | **−62.3 dBm at 438.100 MHz** | −87.8 dBm | Reference for the next gain step |
| 70 dB | −85.8 dBm | **−52.3 dBm at 438.100 MHz** | −83.8 dBm | +10.00 dB relative to the repeated gain-60 run |

All four runs completed without reported stream or cleanup errors and returned to background. A **10 dB gain-setting increase produced a 10.00 dB indicated increase** in the same-setup comparison. Adding nominal pad attenuation gives approximately **−22.3 / −12.3 dBm before the pads** for the repeated gain-60/gain-70 pair. Cable/DC-block loss, pad tolerance and analyzer calibration uncertainty are uncorrected.

## 145.1 MHz spot check

Same wiring, amplitude, rate and analyzer settings; LO changed to 145 MHz. Numerical levels remain after the 40 dB pads:

| TX gain | Before | Tone on | After | Observation |
|---|---:|---:|---:|---|
| 60 dB | −86.6 dBm | −81.6 dBm | −83.1 dBm | Too close to background for clear detection |
| 70 dB | −84.0 dBm | **−73.0 dBm at 145.099 MHz** | −85.0 dBm | Clear tone; no reported stream or cleanup errors |

The gain-70 reading is about **20.7 dB lower** than the earlier 438.1 MHz reading at the same gain. The cause is unresolved; this is an uncalibrated comparison of the complete setup, not an isolated driver-gain measurement.

![tinySA LCD with the 145.1 MHz tone on](images/145mhz-gain70-on.png)
Actual LCD capture during the gain-70 run. Fixed marker: **145.100 MHz, −75.0 dBm**. The screen uses a separate sweep immediately after the numerical scan, so its fixed-marker reading differs from the table's strongest bin within ±5 kHz.

![tinySA LCD after the tone stopped](images/145mhz-gain70-off.png)
Actual LCD capture after stopping; the same marker reads **−87.0 dBm**. Display: 10 dB/div, −40 dBm reference, 145.0–145.2 MHz, external correction still zero. The first 145 MHz run finished before screenshot capture was requested; these images belong to the gain-70 run only.

These checks demonstrate tones through **driver-only Path B** at two frequencies. They do not establish maximum output, final-PA/doubler operation, full frequency response or endurance. Raw bench records are retained separately; selected actual screen captures are included here.

## TX-A low-pass path

After a cold boot, same J10 wiring and gain **70 dB**, amplitude **0.1**, eight-second tones. tinySA internal attenuation changed to **10 dB**; external pads remain **40 dB**. Ultra mode enabled above 800 MHz. Software remains the RAM-only `0c8e7f7` Path B override.

| Channel / selected branch | Tone | Before | Tone on | After |
|---|---:|---:|---:|---:|
| 1 / TX1A, U19 | 438.1 MHz | −101.8 dBm | **−52.3 dBm** | −104.8 dBm |
| 0 / TX2A, U23 | 438.1 MHz | −104.3 dBm | −101.8 dBm | −104.8 dBm |
| 1 / TX1A, U19 | 900.1 MHz | −103.5 dBm | **−56.0 dBm** | −102.2 dBm |
| 1 / TX1A, U19 | 1300.1 MHz | −100.7 dBm | **−64.8 dBm** | −105.7 dBm |
| 1 / TX1A, U19 | 1600.1 MHz | −102.4 dBm | **−82.9 dBm** | −103.5 dBm |

TX1 shows a tone at each point; its indicated output falls above 900 MHz. These are uncalibrated source-to-analyzer measurements, not isolated filter insertion loss. **TX2's expected tone was not detected**; no further TX2 frequency checks were run. No stream errors were reported. The later FPGA-selector check below addresses this missing tone.

![tinySA LCD with the TX1A 1600.1 MHz tone on](images/1600mhz-lowpass-on.png)
Actual LCD capture, fixed marker **1600.100 MHz, −82.5 dBm**.

![tinySA LCD after the TX1A 1600.1 MHz tone stopped](images/1600mhz-lowpass-off.png)
After stopping, fixed marker **−108.4 dBm**. Screens use a separate completed sweep after each numerical scan; table values use the strongest bin within ±5 kHz. Actual on/off screens were retained for every completed check.

One initial 900 MHz capture attempt stopped on a malformed tinySA text value outside the tone window. That attempt is retained separately; one repeat completed the numerical scan and screenshots. No invalid bin was substituted or used for a reported tone level.

## TX-B high-pass path

Same conducted setup, channel **1**, gain **70 dB**, amplitude **0.1** and eight-second tones. Temporary native MPM r9 and Python bindings built from `38ed43e2e5e1821fbd8011333648dc7a7185c972`; explicit `sdrb_tx_path=rf_out_b,sdrb_tx_filter=highpass`. TX1B selects U28; TX2B/U30 remains untested. Both banks also pass through common U32/U13 low-pass filters and the AmpPwr1 drivers.

The rebuilt component first reproduced the low-pass 438.1 MHz tone at **−52.8 dBm**, about 0.5 dB below the earlier reading. For high-pass checks, tinySA uses **5 dB internal attenuation**, LNA off and Ultra mode; the external pads remain 40 dB.

| Selected branch | Tone | Before | Tone on | After |
|---|---:|---:|---:|---:|
| TX1B / U28 | 2000.1 MHz | −110.9 dBm | **−88.6 dBm** | −107.9 dBm |
| TX1B / U28 | 2500.1 MHz | −106.7 dBm | **−74.7 dBm** | −104.2 dBm |
| TX1B / U28 | 3500.1 MHz | −105.1 dBm | −106.1 dBm | −104.9 dBm |
| TX1B / U28 | 5800.1 MHz | −84.0 dBm | −85.5 dBm | −86.0 dBm |

Tones were detected at **2000.1/2500.1 MHz**, but **not at 3500.1/5800.1 MHz**. Background was much higher at 5800 MHz. No stream or cleanup errors were reported. The absent tones do not establish filter rejection or a hardware fault; source/control behavior and the complete RF/measurement path remain unresolved.

![tinySA LCD with the TX1B 2500.1 MHz tone on](images/2500mhz-highpass-on.png)
Actual LCD capture at 5 dB internal attenuation: fixed marker **2500.100 MHz, −75.2 dBm**.

![tinySA LCD after the TX1B 2500.1 MHz tone stopped](images/2500mhz-highpass-off.png)
After stopping, fixed marker **−113.7 dBm**. Numerical peaks and fixed LCD markers come from adjacent sweeps.

The initial 2000/2500 MHz checks used 10 dB internal attenuation and displayed “REDUCED LINEARITY.” Those records are retained; the table uses the repeated checks at 5 dB. The matching [tinySA firmware warning condition](https://github.com/erikkaashoek/tinySA/blob/4eb315d/plot.c#L1891) depends on frequency and configured attenuation.

## TX2 selector correction

The FPGA used MPM's TX-channel-select bit as a codec reset, and the SISO mux selected by nonzero sample data. Corrected RTL separates reset from selection and synchronizes the selector; the old faults reproduce and the corrected regression passes.

Cold-booted **dev.3 + tx-select.1**, FPGA source `a1092059e0d566ae4efb54d0f6bca967df994e57`. Only BOOT.BIN changed, SHA256 `12258ce5e2d2df23681fd751782d198a3baa118cf2e57828bc3568713f9cadde`; Linux/rootfs unchanged, rollback backed up. Boot and software identities verified. Same J10 setup, RAM-only `0c8e7f7` Path B override, **channel 0 / TX2A**, gain 70 dB, amplitude 0.1, 2.304 MS/s, eight seconds. tinySA: 10 dB internal attenuation, Ultra/LNA off, 3 kHz RBW.

| Tone | Before | Tone on | After |
|---|---:|---:|---:|
| 438.100 MHz | −107.2 dBm | **−49.7 dBm** | −102.7 dBm |

The previously missing TX2 tone is now clearly detected through **U23 and J10**. No reported stream or cleanup errors; target metadata read back and SHA256 verified. This establishes one TX2A spot check, without qualifying its full filter response or the separate upper-band issue.

![tinySA LCD with the corrected TX2A 438.1 MHz tone on](images/438mhz-tx2-selector-on.png)
Actual LCD capture: fixed marker **438.100 MHz, −49.7 dBm**.

![tinySA LCD after the corrected TX2A tone stopped](images/438mhz-tx2-selector-off.png)
After stopping: **−103.7 dBm** at the fixed marker. Table values use the numerical peak within ±5 kHz; LCD captures use adjacent completed sweeps.

## Coverage / next check

| Filter | Current evidence through J10 |
|---|---|
| U19, TX1A low-pass | Tone at four selected frequencies, 438.1–1600.1 MHz |
| U23, TX2A low-pass | 438.1 MHz tone demonstrated with tx-select.1 FPGA; absent with original FPGA |
| U28, TX1B high-pass | Tone at 2000.1/2500.1 MHz; absent at 3500.1/5800.1 MHz |
| U30, TX2B high-pass | Not tested |
| U32/U13, common low-pass | Included in the responding paths; individual response and stopband unqualified |

Next: investigate the missing TX1B upper-band tone before extending filter tests. No direct-pad comparison: its coax was removed. The onboard source's 6 GHz ceiling also prevents a complete common-filter stopband check.

Original dev.3 Python and native libraries restored and hash-verified after testing; diagnostic RAM files removed. The test card retains the tx-select.1 FPGA overlay; the published dev.3 image is unchanged. SDRB is powered and idle, MPM active, no claim or failed service. No image build for Ray is planned.

[Back to Lab Log](../../README.md)
