# Session worksheet — BPSK paper/hardware comparison

Copy this file for each session. Blank fields mean not recorded, not zero.
Mark every result as measured, derived, assumed or simulated.

## Identity and question

- Session ID / local date and timezone / operator:
- Test ID T0–T5 / question / one variable being changed:
- Board ID, revision, reworks, supply voltage/current and temperature:
- COMMS/IHU releases, full source SHAs, dirty flags, boot IDs, binary hashes:
- TX/receiver/analysis revisions and exact commands:
- Direction: board TX → SDR, SDR → board RX, or offline replay:
- Previous working configuration / restoration record:

## RF and sampling setup

- Equipment inventory revision / selected physical instrument and pad identities:
- Connection photo / diagram / reference plane:
- Actual source and receiver, firmware/FPGA image, ports and clock sources:
- Requested and measured frequencies, measured CFO and uncertainty:
- Source power measurement, detector/RBW/VBW, calibration and uncertainty:
- Fixed-pad combinations, measured total loss at test frequency, ratings, cables/DC blocks:
- Fresh VNA calibration method/date/reference planes and saved S21 file:
- Historical pad data used only as a reference / current loss and uncertainty:
- Receiver input limit, worst-case calculated input, selected margin:
- Gain/AGC, filter settings and equivalent noise bandwidth:
- Actual sample rate/readback, format/endianness, timestamp origin:
- Symbol rate, mapping, pulse shape, preamble sequence and symbols:
- Native/scored data length, full frame and guard lengths, on-air duration:
- Scope timing observations / baseband bias, headroom and clipping:

## Frozen analysis and run budget

- Expected TX bytes or PRBS definition/seed, sequence and attempt manifest:
- Start time/window alignment method; oracle or acquired timing:
- Receiver mode, CFO correction, estimator window and phase ambiguity handling:
- Noise/CFO/drift/fading injection stage, units, seed and variance convention:
- Input IQ noise estimate and total target Eb/N0; achievable target check:
- Fixed planned bits/packets, capture repeats, spacing, invalidation rules:
- TX-off control duration / baseline before and after sweep:

## Observations and accounting

- Submitted / admitted / completed RF attempts / local failures / unknowns:
- Detected bursts / acquired / erased or unscorable windows:
- Scored bits / bit errors; conditional BER and acquisition coverage:
- Expected frames / unique exact received / CRC failures / missing:
- Forwarded / independently archive-confirmed / duplicates:
- Stream gaps, overflows, underflows, queue peaks and console/timing faults:
- CFO estimate/residual bias and RMSE; phase separation and amplitude imbalance:
- 95% interval method, assumptions, counts and capture-to-capture variation:

## Evidence and interpretation

- Immutable original files, format, storage reference and SHA-256:
- Derived files with input hashes, analysis command and revision:
- Plots: IQ/phase, spectrum, BER/PER, errors versus bit index, CFO residuals:
- What this run establishes:
- Hypotheses / competing explanations / next single-variable test:
- Failures retained and excluded intervals with reasons:
- Shutdown and restored configuration:

[Investigation](../README.md)
