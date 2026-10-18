# 004 LibreSDR TX power check

**Status:** In progress  
**Started:** 2026-10-18  
**Updated:** 2026-10-18

During SDRB testing, the received tone looked weak. Before choosing attenuation
between the radios, I wanted to check what LibreSDR was actually delivering.

## Setup

LibreSDR **TXA → cable/DC block → tinySA Ultra RF INPUT**. There were **no
external pads**. The earlier setup description incorrectly included 30 dB pads;
that was corrected before this isolated measurement. SDRB stayed halted.

LibreSDR used UHD 4.6.0.0 and its verified custom B210-compatible FPGA image.
The source was a complex sine at +100 kHz from a 434 MHz LO, sampled at
2 MS/s, with amplitude **0.1** held fixed. Each run transmitted for 14 seconds.
UHD channel 0 selected `TX/RX`, corresponding to the connected TXA port.

The tinySA Ultra used **30 dB internal attenuation**, LNA off, 3 kHz RBW,
and zero external gain correction. Each scan covered 434.0–434.2 MHz in
201 points. Existing calibration offsets were retained; no fresh calibration
was performed. [Exact setup and software identities](files/setup.json).

## Measurements

One scan before, during and after each transmission:

| UHD TX gain setting | Tone frequency indicated | TX-on level | TX-off peak before / after¹ |
| --- | --- | --- | --- |
| 20 dB | 434.099 MHz | −62.6 dBm | −85.6 / −83.6 dBm |
| 40 dB | 434.099 MHz | −42.5 dBm | −83.1 / −83.5 dBm |

¹ Maximum within ±5 kHz of nominal 434.1 MHz. These background peaks need
not occupy the same bin as the transmitted tone.

Increasing the gain setting by 20 dB increased the indicated tone level by
**20.03 dB**. The tone appeared with transmission and disappeared after stopping.
Both source runs completed without reported TX events or reference RX errors.

## What this establishes

These are **analyzer-indicated levels at the end of the cable/DC-block chain**.
Cable and block losses were not measured or removed. Gain settings are not dBm,
and this fixed-amplitude, single-frequency check does not establish maximum
output, frequency response, harmonics or absolute calibration accuracy.

The measured source levels give us a basis for choosing attenuation rather
than assuming a fixed 30 dB pad. SDRB receive behavior and its return TX level
remain separate checks; this measurement does not qualify the complete link.

[Gain-20 results](files/gain-20-result.json) ·
[Gain-40 results](files/gain-40-result.json).
Raw before/active/after analyzer scans are alongside them in [files](files/).

[Back to Lab Log](../../README.md)
