# 003 EMBER transceiver bring-up

**Status:** In progress  
**Started:** 2026-10-15  
**Updated:** 2026-10-15

The EMBER transceiver PCB arrived today. I am bringing it up in stages, starting
with unpowered checks before testing the supplies, controller, CAN interfaces,
and RF paths.

## Initial inspection and setup

I inspected the board under the microscope and did not see any solder bridges.
That is a visual observation; electrical shorts and assembly correctness have
not yet been ruled out by measurement.

The Pico and H1/H2 headers are not installed. Nothing has been connected to
the board: no supply, USB, or external interfaces. A multimeter and a NANKADF
current-limited bench supply are available. The supply model, multimeter model,
and individual board identifier have not yet been recorded. I plan to solder
one temporary power pin and one ground pin for the first tests.

## Unpowered supply resistance

With the Pico absent and the board disconnected, I measured:

| Measurement | Reported resistance |
| --- | --- |
| Meter probes touched together | 0.34 Ω |
| Across C117 — input 5 V to GND | 20 kΩ |
| Across C58 — protected 5 V to GND | 359 kΩ |
| Across C59 — 3.3 V to GND | 20 kΩ |

These readings do not indicate a hard short on the three measured rails. They
do not yet establish correct powered operation. The reported readings were taken after approximately 10 seconds of settling.
Initial readings and actual probe polarity were not separately recorded; no
lead-resistance correction has been applied.

## Power connection checks

The ordered-board pad record identifies H2 pads 25/26 as input `+5V_CON` and
H2 pads 29–32 as GND. Proposed temporary connections are H2 pad 25 for positive
and pad 29 for ground. Subsequent reported measurements were:

| Measurement | Reported resistance |
| --- | --- |
| H2 pad 25 → C117 pad 1 | 1.14 Ω |
| H2 pad 25 → C117 pad 2 | 2.38 MΩ |
| H2 pad 25 → H2 pad 29 | 5.3 MΩ |

The first reading suggests continuity along the input rail, but is above the
previous 0.34 Ω shorted-lead reading. Probe contact should be checked before
attributing that difference to the PCB. The two megohm readings differ from
the earlier 20 kΩ across C117. Probe polarity, settling time and contact for
this set were not recorded, so the discrepancy remains unresolved. Neither
measurement directly verifies H2 pad 29's connection to C117 ground.

### Correcting the measurement point

I found that I had been measuring the wrong pin and corrected the measurement
point. H2 pad 29 to C117 pad 2 then measured **1.3 Ω**, suggesting ground
continuity. It has not been clarified which earlier readings used the wrong
pin, or whether the correction involved only a probe or a soldered test pin;
the earlier readings are retained rather than treated as verified connections.

Repeating input-to-ground resistance at H2 pads 25/29 gave **4 MΩ and climbing**.
The requested orientation was red on pad 25 and black on pad 29. This is not a
settled value. A rising reading can result from the meter charging capacitance;
it does not indicate a hard short or establish powered operation.

## Next check

With power disconnected, compare directly across C117 using the same probe
polarity (red on pad 1, black on pad 2). Confirm whether the wrong-pin correction
was probe placement only or also a change to a temporary soldered connection.
Then establish the current-limited first-power setup.

No power-on results are recorded. Pico and external interfaces remain outside
the proposed first-power setup.

[Related antenna investigation](../001-ember-antenna/README.md) ·
[Back to Lab Log](../../README.md)
