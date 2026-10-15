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
continuity. The correction was moving the probe only, not relocating a soldered pin.
Which earlier readings used the wrong pin was not specified; those readings
are retained rather than treated as verified connections.

Repeating input-to-ground resistance at H2 pads 25/29 gave **4 MΩ and climbing**.
The requested orientation was red on pad 25 and black on pad 29. This is not a
settled value. A rising reading can result from the meter charging capacitance;
it does not indicate a hard short or establish powered operation.

Directly across C117, the subsequent reading was **OL**. This indicates the
meter was over range, not a measured infinite resistance. Together with the
high/rising input reading, this check has not identified a hard input-to-ground
short. The earlier 20 kΩ observation remains in the record; its difference is
not assigned a confirmed cause.

## First current-limited power-on

I confirmed the NANKADF settings at **5.0 V / 0.050 A**. The requested
connection was positive to H2 pad 25 and negative to H2 pad 29, with the Pico,
USB and other interfaces disconnected. The procedure called for a 1–2 second
power-on followed by output off; actual elapsed time and final output state
were not separately reported.

| Supply indication | Reported value |
| --- | --- |
| Output voltage | 2.95 V |
| Output current | 0.050 A |
| Regulation mode | CC |

The supply reached its current limit and did not hold the requested 5.0 V.
The 50 mA limit was deliberately conservative, not an operating-current budget.
This result alone does not distinguish normal circuit demand from a fault and
is not a successful nominal-voltage bring-up. These are supply-display values;
voltage at the board input and after U15 has not yet been measured.

### Input and protected-rail voltages

At the same 5.0 V / 50 mA supply settings, I measured **2.96 V across C117**
(board input) and **2.94 V across C58** (protected 5 V rail). Their approximately
20 mV difference shows the protection path is passing voltage in this condition.
The readings were taken separately; this is not a precision simultaneous drop
measurement or full qualification of U15. The board remains below nominal supply
voltage, and its normal operating current is still unknown.

### 100 mA current-limit step

With the supply set to 5.0 V and a 100 mA limit, the display read **3.89 V,
0.100 A, CC**. I noticed no smoke or heat during the check; no temperature
measurement was recorded. Voltage rose from the previous current-limited test,
but the board still did not reach nominal input voltage. Normal operating
current and the cause of the load remain unqualified.

## Next check

With output off, retain the 5.0 V setting and increase the current limit to
150 mA for another brief 1–2 second observation. Record actual supply voltage,
current and CV/CC mode, then turn output off. This is a staged diagnostic limit,
not an approved operating-current budget. Do not increase it further without
reviewing the result. Stop immediately for smoke, odor or obvious heating.

[Related antenna investigation](../001-ember-antenna/README.md) ·
[Back to Lab Log](../../README.md)
