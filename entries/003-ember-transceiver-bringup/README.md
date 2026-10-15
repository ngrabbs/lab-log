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

## Next check — unpowered supply resistance

With the board disconnected, identify the ground and supply measurement points
against the ordered design. Measure resistance from each supply rail to ground,
recording probe polarity and both the initial and settled reading. Capacitors
may make the reading change; a continuity beep alone is not a resistance result.
No resistance measurements or power-on results have been recorded yet.

After reviewing those readings, establish the power connection and current limit
for the first controlled power-on. Keep the Pico and external interfaces
disconnected for the initial supply checks.

[Related antenna investigation](../001-ember-antenna/README.md) ·
[Back to Lab Log](../../README.md)
