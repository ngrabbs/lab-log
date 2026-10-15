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

### 150 mA current-limit step

At the 5.0 V setting and 150 mA limit, the supply displayed **4.97 V,
0.150 A, CC**. No smoke was observed. This is close to the requested voltage,
but the reported CC state means current limiting was still active; a stable
constant-voltage operating current has not yet been established.

### First constant-voltage result

At the 5.0 V setting with a 200 mA current limit, the supply displayed
**5.0 V, 0.150 A, CV**. No smoke was observed. This is the first reported
constant-voltage result, with current below the selected limit. The indicated
input power is approximately **0.75 W** (5.0 V × 0.150 A). It is a brief
observation, not a sustained-current or thermal qualification, and the Pico
is still absent.

### Board voltages at nominal input

The next measurements were **4.99 V across C117** and **4.97 V across C58**.
The approximately 20 mV difference is consistent with the earlier protection-path
check. The supply's current and mode were not separately reconfirmed with these
two readings. This establishes near-nominal voltage at both measured board nodes,
not yet all supply rails or functional operation.

### Lower-rail measurements with only 5 V applied

I measured **3.0 V across C105** and **0 V across C59**. C105 is on the local
`+3V0` regulator output; C59 is on the externally supplied `+3V3` rail. These
results show nominal voltage at the local 3.0 V measurement point and no measured
voltage on the unsupplied 3.3 V rail. Supply current and CV/CC mode were not
separately reconfirmed for this pair of readings.

The 5 V input/protected rail and local 3.0 V checks are encouraging, but this
is still a partial-power test. The 3.3 V-powered circuitry has not been brought
up. The Pico remains absent; installing it is not a substitute for verifying
the board's external 3.3 V supply arrangement.

## Preparing the second supply channel

A second channel capable of 3.3 V is available and reported connected, ready
for testing. Exact channel settings and its physical connection points have
not yet been reported. No dual-rail power-on result is recorded yet.

Proposed next procedure, with Pico/USB/CAN still disconnected:

1. Turn both outputs off. Use independent channels, not series or parallel mode.
   Confirm 5 V positive goes to H2 pad 25, 3.3 V positive to H2 pad 27 (or 28),
   and both negatives share board GND at H2 pad 29 (or another verified GND pad).
2. With sources disconnected, check the new positive connection to C59 pad 1
   and its ground connection to C59 pad 2 for low resistance. Return the meter
   to DC volts before powered measurements.
3. Set the 5 V channel to 5.0 V / 200 mA and the new channel to 3.30 V / 50 mA.
   The latter is an initial screening limit, not an established operating budget.
4. Enable 5 V first, then 3.3 V. Observe both channels for 1–2 seconds and record
   each voltage, current and CV/CC mode. Turn 3.3 V off, then 5 V off. Do not
   increase either current limit if it enters CC; review the readings first.

This order continues the already-tested 5 V-only configuration before adding
logic power; it is not a claim of complete board power-sequencing qualification.
Stop for smoke, odor or obvious heating. Board-rail measurements follow only
after the supply readings are reviewed.

## Identifying the second supply

I reported powering the 3.3 V connection, seeing the board's 3.3 V power LED
illuminate, and seeing the 5 V supply remain up. No numerical board voltage or
3.3 V current was recorded during that check. The second source did not have
the adjustable current limit assumed in the proposed procedure, so that
procedure was not completed as written.

Desktop inspection identified **WaveForms 3.25.1 with an Analog Discovery 3
rev C**, separate from the NANKADF 5 V source. At inspection, Master Enable
was off, the positive-supply setpoint was **3.004 V**, the negative supply was
disabled, and Hardware Power Limit was **Auto / 2.5 W**. This later UI snapshot
does not establish the voltage setting during the preceding LED observation.
No supply settings or output enables were changed during inspection.

The [Digilent manual](https://files.digilent.com/manuals/WaveForms/3.24.4/start10.html)
describes a shared adjustable power limit (0.6–15 W); it is not an adjustable
50 mA output-current limit. The displayed USB current is instrument input
current, not a measurement of current into the board's 3.3 V rail. Before the
next test, correct/verify the positive-supply setting at 3.30 V and establish
an appropriate protection and current-measurement arrangement. The next test below establishes the board voltage with both sources applied.

## Both supplies applied

For the next test, the requested settings were NANKADF **5.0 V / 200 mA** and
AD3 **V+ 3.30 V / 0.6 W hardware power limit**, with V− disabled and common
board ground. The procedure enabled 5 V first, then AD3, and called for AD3
to be switched off before 5 V after measurement. Those settings are the
requested procedure, not an independently captured instrument configuration.

I measured **3.29 V across C59**, saw **no WaveForms warnings**, and read
**0.149 A on the 5 V supply**. This confirms near-nominal external 3.3 V at the
board. The 5 V current is close to the earlier 150 mA observation; the 1 mA
difference is not interpreted as significant without instrument accuracy data.
Current into the 3.3 V rail remains unmeasured, so 149 mA is not total board
current or a complete power budget. No sustained or thermal qualification is
claimed.

### Pico supply feed

The reported voltage from **J7 pad 2 (PICO_VSYS) to J7 pad 3 (GND)** was
**4.9 V**, with the Pico still absent. This confirms voltage reaches the
Pico supply connection downstream of D14. It is an unloaded measurement at
that connector; startup with the Pico and its additional current remain untested.

## Next check

Keep both outputs off and identify the exact Pico variant and currently loaded
firmware before installation. Prepare a controlled bring-up image with RF/clock
outputs disabled before using the controller on the board. The supply measurements
do not yet establish MCU operation, CAN communication, clock generation or RF
performance. No controller installation or firmware change has been recorded.

## Bare Pico firmware inspection

I identified the controller as an original Raspberry Pi Pico, already running
transceiver comms firmware, and booted it separately with its USB console
available. It has not been installed on the new board.

A passive serial capture, with no commands sent, received:

```text
[comms] heartbeat #15  uptime=78192 ms  tasks=5  free_heap=119888  ihu=0 xacts
```

This confirms live firmware console output on the bare Pico. The boot report
was not captured, and the flashed binary was not read back or matched to a
source/build hash. No firmware was flashed and no reset or RF commands were sent.

The inspected source checkout was at EMBER commit
`9b714354fd0ca63ff51502d462ad13d26b3a837f`. Its older comms configuration uses
GP14/GP15 for an I²C housekeeping slave. The ordered PCB uses those GPIOs for
CAN_A_CSn / CAN_B_CSn at J6 pads 19/20. That source is therefore not suitable
unchanged for the current dual-CAN board. Its startup code drives TX_ACTIVE and
BPSK_DATA low and performs a read-only Si5351 status probe, but this source
inspection is not proof of the exact behavior of the flashed image.

Next: prepare and verify firmware against the ordered board pin map, keeping
RF muted and clock outputs explicitly controlled, before installing the Pico.

[Related antenna investigation](../001-ember-antenna/README.md) ·
[Back to Lab Log](../../README.md)
