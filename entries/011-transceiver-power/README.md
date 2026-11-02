# 011 EMBER transceiver power consumption and RF output

**Status:** In progress  
**Started:** 2026-11-02  
**Updated:** 2026-11-02

The transceiver has demonstrated packet transmission and reception. Now I want to measure what it costs to operate: idle and listening power, energy per telemetry packet, and RF power delivered at the antenna connector. The new Nordic PPK2 should make the current measurements much easier than a separate shunt and oscilloscope setup.

This is the test plan for today's session. No measurements have been taken for this entry yet. The earlier [transceiver bring-up](../003-ember-transceiver-bringup/README.md) remains the record of functional testing.

## Questions to answer

- How much power does the board draw while idle, handling CAN traffic, listening, and transmitting?
- What are the peak current and total energy of a telemetry packet or command/reply transaction?
- How much conducted RF power reaches J9 during a tone and during a packet?
- What average power should the spacecraft budget for a specified telemetry cadence?
- What fraction of board input power becomes useful RF output?

## Equipment and measurement boundary

The [equipment inventory](../../equipment/README.md) identifies the Nordic NRF-PPK2, NANKADF bench supply, ANENG AN8008 and Uni-T DT-9205B+ meters, Rigol DS1202Z-E, Analog Discovery, tinySA Ultra, NanoVNA-F V2, DC blocks, and attenuators. The GODIYMODULES reference module provides nominal voltage/resistance points for meter checks; its actual values and traceability have not been established.

Measure the transceiver's own supply feeds, not the entire stack. Before connecting instruments, confirm the present board revision, power wiring and firmware. If both 5 V and 3.3 V are supplied externally, measure both. USB or signal connections must not provide an unmeasured parallel supply path. Record whether LEDs, Pico, CAN termination and external interfaces are fitted/enabled.

The PPK2 will initially be used in **Ampere Meter mode**, with the bench supply powering one rail through it:

```text
Bench supply positive → PPK2 VIN → PPK2 VOUT → selected board supply rail
Bench supply ground ─────────── PPK2 GND ─── board ground
Other required board rail → separate appropriate supply
```

Use a DMM at the board to measure actual rail voltage. The PPK2 measures current on one feed; it does not simultaneously measure both rails. Repeat the same controlled sequence for the second rail and combine energies only when the runs are repeatable. Do not combine the two rail voltages onto one profiler input.

Nordic specifies 100 kS/s sampling, 0.8–5.0 V operation, and maximum current of 1 A continuous in Ampere Meter mode or 600 mA in Source Meter mode. Verify actual supply voltage, including overshoot, before connecting the 5 V feed. Use the profiler within these limits. Keep the Rigol for rail droop and fast transitions; connect its probe grounds only to board ground.

RF measurements use a conducted path, with no antenna:

```text
Transceiver J9 → DC block → known external attenuation → tinySA RF IN
```

Start with a known 30 dB pad and bounded low-output testing. Confirm pad identity, power rating and analyzer input limits before transmitting. The analyzer and attenuator provide the terminated measurement path. Do not substitute the unverified HF dummy load or unidentified one-port barrel device for a qualified UHF load.

## Planned procedure

### 1. Record the setup and check the instruments

1. Photograph the board and wiring. Record board/rework revision, firmware version/commit/dirty flag, supply arrangement and room temperature if available.
2. Record PPK2 firmware/app version, DMM ranges, supply settings, tinySA configuration and NanoVNA calibration setup. Confirm that no other session or scheduled task will key the transmitter during wiring changes.
3. Check both DMMs against the reference module at nominal 2.5 V and 5 V, following its power and loading requirements. Record the indicated values without adjusting either meter to match an uncalibrated reference. The 7.5/10 V outputs must not be connected to the PPK2 or board supply inputs.
4. Check PPK2 zero/no-load behavior. If a suitable known load is available, compare its steady current with a DMM in a separate series-current check. Do not place a meter's current input across a supply. The reference module's resistor network is not assumed to be a power-rated load or a low-value current shunt.
5. With board power off, insert the PPK2 into the chosen positive supply feed. Confirm alternate power paths, then enable current-limited power and verify board voltage and idle current. Record any burden-voltage effect.

### 2. Capture idle, receive and transmit consumption

Use 100 kS/s current acquisition if supported by the installed app, and retain raw captures. Suggested baseline is 10 seconds of settled idle. Repeat each active condition at least five times with fixed packet bytes/length and recorded settings; retain failures and outliers.

| Condition | Controlled activity | Measurement |
| --- | --- | --- |
| Idle | RF muted; CAN ready; no intentional traffic | Mean current, background activity |
| CAN only | Known bounded traffic; RF muted | Change above idle |
| RX listening | Receiver active; no intentional RF input | Listening current and startup transient |
| RX packet | Known packet at fixed measured input level | Capture/decoding current and duration |
| TX tone | Bounded CW diagnostic at recorded frequency/settings | Steady TX current and rail droop |
| TX telemetry | Fixed packet; bounded individual transmission | Peak current, charge and energy |
| Command/reply | One valid PING and one correlated reply | Total transaction energy and latency |

Start with idle and TX before adding receive stimulation. Initial tone duration should be no more than one second and remain within the installed firmware's existing limits. Do not extend a hardware mute or watchdog to obtain a convenient trace. If supported, use the PPK2 digital inputs for a compatible TX-active or firmware event marker; otherwise preserve console timestamps and record the timing uncertainty. Confirm logic voltage limits before attaching digital leads.

Repeat on the other supply rail after powering down and moving the profiler. Keep operating conditions unchanged. Measure rail voltage at the board during each state and use the Rigol if transitions show droop. A single profiler cannot establish simultaneous two-rail peak power from separate captures.

### 3. Measure the RF output

1. With the transmitter disabled and disconnected, calibrate the NanoVNA for the current cables/reference planes. Measure the insertion loss of the actual DC block, pads and cable chain near the chosen TX frequency. Save calibration details and Touchstone data.
2. Reconnect J9 to tinySA through that chain. Set input mode, generator off, LNA off, and explicit internal attenuation. Record RBW/VBW, detector, span, reference level and external correction setting.
3. Capture RF-off, one bounded CW burst, and RF-off again. Synchronize the measurement to the burst; a noise-only trace or a missed sweep is not an output-power reading.
4. Repeat five times at unchanged settings. Check a second attenuation setting or known additional pad: corrected source power should agree within the measurement uncertainty. Investigate disagreement before interpreting it as transmitter behavior.
5. Measure real packet power over a defined occupied channel bandwidth. A single spectrum peak is not total BPSK channel power. Record whether the measurement is during the burst or averaged over the entire duty cycle. If tinySA cannot reliably capture the short burst, use a calibrated relative SDR capture referenced to the measured tone, and label that method separately.
6. Repeat selected DC/RF measurements after warm-up. Record elapsed time and any supply changes.

The old [attenuator measurements](../../equipment/characterizations/attenuators/README.md) are useful comparisons, not a calibration of today's chain. Internal analyzer attenuation is normally already included in its displayed input level. Apply external path correction exactly once.

## Calculations and accuracy

For each externally supplied rail, calculate power at the board terminals: `P = V × I`. Sum rail powers for total board consumption. For a stable rail, `E = V × integral(I dt)` and charge is `Q = integral(I dt)`. If voltage varies materially, use time-aligned voltage/current measurements or bound the energy error; do not treat a fixed supply setting as measured instantaneous voltage.

Report both total event energy and the incremental energy above a same-duration idle baseline. For non-overlapping periodic events, average power can be estimated as `P_idle + incremental_event_energy / period`. Include listening time and any other activity in the operating schedule.

At the antenna connector, `P_RF(dBm) = analyzer_input(dBm) + external_path_loss(dB)`, with corrections already applied by the analyzer accounted for. Convert with `P_RF(mW) = 10^(dBm/10)`. Whole-board TX efficiency is useful in-band RF output divided by total DC input during the same TX state; it is not amplifier-only efficiency. For packet efficiency, use matched RF and DC event-energy windows.

Keep repeatability separate from absolute accuracy. Record DMM accuracy/range, PPK2 range-dependent accuracy and insertion effects, reference-module uncertainty, path loss/mismatch, analyzer calibration and burst-capture uncertainty. Do not claim a percentage accuracy before evaluating these terms. As an illustration, ±1 dB corresponds to roughly −21%/+26% in watts. DC measurements cannot calibrate the tinySA's RF amplitude response.

## Results to fill during the session

**No results recorded yet.** Dashes below mean not measured, not zero.

| State/run | Rail | Board V | Mean mA | Peak mA | Window ms | Charge µC | Total energy mJ | Raw file |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Idle | — | — | — | — | — | — | — | — |
| RX listening | — | — | — | — | — | — | — | — |
| TX tone | — | — | — | — | — | — | — | — |
| TX packet | — | — | — | — | — | — | — | — |
| Command/reply | — | — | — | — | — | — | — | — |

| RF run | Frequency MHz | CW/packet | Analyzer dBm | External loss dB | J9 dBm / mW | Measurement window/bandwidth | Raw file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pending | — | — | — | — | — | — | — |

Save original PPK2 captures/exports, scope waveforms, tinySA traces, NanoVNA files, setup photos and exact command/firmware identities under this entry as they are collected. Keep calculations separate from original files, and omit private host details and credentials.

## Current outcome and next step

The plan is ready; board consumption, RF output and efficiency remain unmeasured in this entry. First confirm the present supply arrangement and identify/connect the PPK2 without changing the board wiring while powered. Then perform the meter checks and capture the first idle baseline. No flash, RF transmission or live instrument action was performed while writing this plan.

## References

- [Equipment on hand](../../equipment/README.md) and [attenuator characterization](../../equipment/characterizations/attenuators/README.md).
- Nordic: [PPK2 overview](https://docs.nordicsemi.com/r/bundle/ug_ppk2/page/ug/ppk/ppk_user_guide_intro.html), [supply modes and voltage limits](https://docs.nordicsemi.com/r/bundle/ug_ppk2/page/ug/ppk/ppk_power_supply.html), [maximum DUT current](https://docs.nordicsemi.com/r/bundle/ug_ppk2/page/ug/ppk/ppk_max_dut_current.html).
- tinySA: [transmitter measurements](https://www.tinysa.org/wiki/pmwiki.php?n=Main.Transmitters), [channel power](https://tinysa.org/wiki/pmwiki.php?n=Main.MEASURE2).
- [Related transceiver bring-up](../003-ember-transceiver-bringup/README.md).

[Back to Lab Log](../../README.md)
