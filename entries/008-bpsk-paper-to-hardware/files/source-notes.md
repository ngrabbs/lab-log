# Sources reviewed for the October 23 plan

This is a provenance record, not a record of installed firmware or new bench tests.
No full paper, firmware binary, private host details or unrelated project files
are republished with this plan.

## Course project

User-supplied project directory: ECE-4813 Communications Theory / Project.
The plan's paper statements were checked against `overleaf/main.tex` and the
implementation in `matlab_submission/main.m`, `estimate_frequency_offset.m` and
its README. The MATLAB driver was inspected, not executed. An existing CSV in
the top-level `data/` directory was also inspected, but is not assumed to be output
from the exact reviewed MATLAB version; no new simulation result is claimed.

SHA-256 identities:

| Artifact | SHA-256 |
| --- | --- |
| `overleaf/main.tex` | `8fb05a410b9ac12cddc4a280b2ec2262add52b829fe19a2905ba0ba58585da03` |
| `matlab_submission/main.m` | `10a505c6135a493d87d2960340860cffd8bee35981fd23a6388ccc4725f88fc3` |
| `final_submission/BPSK_Performance_Analysis_20260725.pdf` | `f60c23d42d1df69732b0596f506515d4dc5efe8fae91a86bd0bc5c98262cd320` |

The PDF was identified by hash, not used as a verified rendering of the TeX source.
Before rerunning the exact submitted study, reconcile the submitted archive/PDF
with the reviewed sources and archive all inputs separately from new outputs.

## EMBER

The supplied local checkout was at `bf34212bbf0c1c9d02e7b2b58911f59e1178e826`
and had unrelated working changes. It was read only. Its `firmware/comms/` README,
clock bring-up code, TX/RX chain documentation and bring-up test plans establish
design context but predate the current BPSK packet runtime.

GitHub source inspected at immutable commit
[`06680f3d256bc71e107fe5be377b929e5bf25033`](https://github.com/ngrabbs/ember/commit/06680f3d256bc71e107fe5be377b929e5bf25033):

- [Ground BPSK documentation](https://github.com/ngrabbs/ember/blob/06680f3d256bc71e107fe5be377b929e5bf25033/ground/bpsk/README.md)
- [Ground differential decoder](https://github.com/ngrabbs/ember/blob/06680f3d256bc71e107fe5be377b929e5bf25033/ground/bpsk/modem.py)
- [Transmitter packet framing](https://github.com/ngrabbs/ember/blob/06680f3d256bc71e107fe5be377b929e5bf25033/firmware/transceiver/bpsk_packet.h)
- [UHF admission and local result contract](https://github.com/ngrabbs/ember/blob/06680f3d256bc71e107fe5be377b929e5bf25033/system/interfaces/transceiver_uhf_bench.md)
- [Board ADC capture analysis](https://github.com/ngrabbs/ember/blob/06680f3d256bc71e107fe5be377b929e5bf25033/ground/bpsk/adc_capture.py)
- [Bounded uplink source](https://github.com/ngrabbs/ember/blob/06680f3d256bc71e107fe5be377b929e5bf25033/ground/bpsk/uplink_probe.py)
- [Finite round-trip probe](https://github.com/ngrabbs/ember/blob/06680f3d256bc71e107fe5be377b929e5bf25033/ground/bpsk/roundtrip.py)

Current interface documentation describes COMMS 0.33.0 / IHU 0.14.0, while older
sections in ground documentation and entry 003 describe earlier versions and
console procedures. Do not combine those procedures or assume either version is
installed. Query the actual bench identities and follow their matching revision.
No copied operational command sequence is required to carry out this plan's
first read-only setup and offline work.

Historical hardware evidence: [entry 003](../../003-ember-transceiver-bringup/README.md)
as present at lab-log commit `3fe48ee827fbda0eca4fa07b805c75ad623e9c87`.
The reported phase angles and 185/185 demonstration belong to that entry's
conditions; they have not been independently remeasured here.

## Supporting analytical references

- [MathWorks: analytical BER expressions](https://www.mathworks.com/help/comm/ug/analytical-expressions-used-in-berawgn-function-and-bit-error-rate-analysis-app.html): distinguishes coherent BPSK, coherently detected differential encoding, and two-symbol DPSK detection.
- [MathWorks: AWGN channel conventions](https://www.mathworks.com/help/comm/ug/awgn-channel.html): distinguishes per-sample SNR, Es/N0 and Eb/N0, including the complex-sample oversampling relation.

## Equipment reference added on October 23

Reviewed the [shared inventory](../../../equipment/README.md) and
[attenuator characterization](../../../equipment/characterizations/attenuators/README.md)
at lab-log commit
[`3d86e5384536a5a2fa6e4add99244a89908b8bdd`](https://github.com/ngrabbs/lab-log/commit/3d86e5384536a5a2fa6e4add99244a89908b8bdd).
Checked the original `nooelec_20_and_10dB_20260517.s2p` and
`nooelec_all_pads_41dB_20260517.s2p` files: their complex S21 samples at
434808900 Hz give 29.5558 and 41.1330 dB attenuation respectively. These
independently recalculated historical samples support the rounded values in the
plan; no new VNA acquisition, uncertainty assessment or power test was performed.
The inventory distinguishes recorded ownership from unconfirmed orders and
access, and is the reference for equipment planning. Its scope model is
DS1202Z-E; the earlier conversation used the shortened DS1202-Z name.
The RF generator's identity/access and Analog Discovery generation remain
unconfirmed, so neither is required for the first session.

The present successful-packet report and initial equipment list were supplied by
the user on 2026-10-23. Proposed sweep values, budgets, tolerances to investigate and
additional diagnostic tooling are plans, not measured capabilities.

[Investigation](../README.md)
