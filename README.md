# Lab Log

A running log of things I build, test, fix, and investigate. Written for future me and anyone who wants to follow along or try it themselves.

I miss the old forum build threads: the problem, the pictures, the experiments, the wrong turns, and how someone finally got it working. That is the idea here. Each entry keeps an investigation together, even when it takes several days.

**[Equipment on Hand](equipment/README.md)** — instruments, radios, tools, availability notes, and measured characterizations.

**[Components and parts](components/README.md)** — recorded stock, orders awaiting receipt confirmation, and [toroid stock](components/toroids.md).

## Entries

Newest entries first. Ongoing investigations are updated on their own page.

| No. | Entry | Description |
| --- | --- | --- |
| 014 | [Moon Base relay contact replay](entries/014-moon-base-relay-replay/README.md) | Python and live BPv7 contact replay. At 5 KiB/s the three-policy LilyGO replay delivered 900 FIFO, 1,042 alerts-first, and 898 alerts-then-FIFO records by cutoff. In progress. |
| 013 | [CaribouLite conducted S-band QPSK science downlink](entries/013-cariboulite-sband-qpsk/README.md) | 2250 MHz QPSK goodput and loss at 250 and 500 ksym/s. The 2 MS/s profile delivered 2.66 Mbps of payload with zero observed packet loss over 10,240 frames. In progress. |
| 012 | [Timing the EMBER fire detector on the Raspberry Pi 4](entries/012-pi-fire-benchmark/README.md) | Per-triplet results and runtimes for EGSE, phase fallback, and Jacob’s JPEG methods. In progress. |
| 011 | [EMBER transceiver power consumption and RF output](entries/011-transceiver-power/README.md) | Planned PPK2 current/packet-energy measurements and conducted RF output checks. No measurements yet. In progress. |
| 010 | [Two-minute EMBER-format FM beacon](entries/010-ember-fm-beacon/README.md) | Outpost1/Baofeng to SatNOGS: four native-format 1200-baud packets decoded; CW KI5YNG and outdoor two-minute timing verified. In progress. |
| 009 | [BPSK audio over FM to outpost1](entries/009-bpsk-over-fm/README.md) | UV-K5/Digirig to RTL-SDR: 9/9 CRC-valid packets across outpost1 and an outdoor SatNOGS J-pole; barrel load, raw IQ, code and measured comparisons. In progress. |
| 008 | [SDRB J14 doubler drive check](entries/008-sdrb-j14-drive-check/README.md) | J14 gain checks and a detected 5.184 GHz J10 fundamental; actual tinySA screens and results tables. In progress. |
| 007 | [SDRB RF_Out check](entries/007-sdrb-rf-out/README.md) | Four TX branches; rc.5 limited TX CLI qualification: four J10 branches, RAM playback and SIGINT/restart pass; earlier failures retained. Intermittent forwarding underflow remains open. In progress. |
| 004 | [LibreSDR TX power check](entries/004-libresdr-tx-power/README.md) | Two-point 434.1 MHz check: −62.6/−42.5 dBm through the cable/DC block; off/on/off contrast verified. In progress. |
| 003 | [EMBER transceiver bring-up](entries/003-ember-transceiver-bringup/README.md) | 11.5-minute UHF demo passed: 185/185 packets, live dashboards and controlled overflow mitigation tested. RF/RX qualification remains open. In progress. |
| 002 | [Gathering daylight fire and no-fire images](entries/002-kline-daylight-burn/README.md) | Leaves and small branches burned in two daylight setups. Example images, exposure settings, and JPEG brightness measurements; preliminary analysis kept separately. In progress. |
| 001 | [EMBER UHF antenna testing](entries/001-ember-antenna/README.md) | Nitinol dipole experiments, feed troubleshooting, and copper reference tuning with a NanoVNA. In progress. |

## Writing an entry

Start with the [entry template](templates/entry.md). The [writing guidelines](AGENTS.md) keep the notes useful and grounded in what actually happened.
