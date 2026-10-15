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

The Pico is not installed. Nothing has been connected to the board: no supply,
USB, or external interfaces. A multimeter and a current-limited bench supply
are available. Instrument models and the individual board identifier have not
yet been recorded.

## Unpowered supply resistance

With the Pico absent and the board disconnected, I measured:

| Measurement | Reported resistance |
| --- | --- |
| Meter probes touched together | 0.34 Ω |
| Across C117 — input 5 V to GND | 20 kΩ |
| Across C58 — protected 5 V to GND | 359 kΩ |
| Across C59 — 3.3 V to GND | 20 kΩ |

These readings do not indicate a hard short on the three measured rails. They
do not yet establish correct powered operation. Initial versus settled values
and actual probe polarity have not been separately confirmed; these are the
reported readings, without lead-resistance correction.

## Next check

Confirm that the readings settled, then identify the supply connection and
set the bench voltage/current limit for first power. Keep the Pico and external
interfaces disconnected. No power-on results have been recorded yet.

[Related antenna investigation](../001-ember-antenna/README.md) ·
[Back to Lab Log](../../README.md)
