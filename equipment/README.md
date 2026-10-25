# Equipment on Hand

**Updated:** 2026-10-25

**Inventory status:** Seeded from older testbed records; reconciliation in progress.

This is the reference for equipment available for experiments in Lab Log. Check here before asking what gear I have or proposing a purchase. It covers instruments, radios, antennas, supplies, fabrication tools and software; detailed measurements live in the linked characterization pages.

**Recorded owned** means the testbed inventory listed it as owned, not that it was inspected again on the update date. Use that as the planning baseline; ask about current availability only when the task depends on it. **Unconfirmed** marks ambiguous, ordered, shared or unspecified availability. Listed ranges and power ratings below come from the source notes and have not been reverified as manufacturer specifications. Measured performance is identified by a dated record.

## Quick links

- [Attenuator characterization and original files](characterizations/attenuators/README.md)
- [Items to confirm](#items-to-confirm)
- [Othermill V2, tooling and stock](#othermill-v2-tooling-and-stock)
- [Software](#software)
- [Source and maintenance](#source-and-maintenance)

## RF measurement and test gear

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| NanoVNA | Documented in October lab entry | NanoVNA-F V2 identified in [entry 001](../entries/001-ember-antenna/README.md), firmware 0.5.4. May characterization instrument identity is not recorded; do not assume it was the same unit. Full supported range and calibration status need confirmation. |
| TinySA | Documented in October lab entry | tinySA Ultra identified in [entry 007](../entries/007-sdrb-rf-out/README.md), firmware tinySA4_v1.4-156-g4eb315d. Older inventory model unknown is superseded. Absolute calibration status remains unconfirmed. |
| RF signal generator | Reported available; model unknown | Listed among available instruments in [entry 001](../entries/001-ember-antenna/README.md), superseding the older testbed wanted item. Exact model, range, output accuracy and present availability need confirmation. |
| Pacific Antenna Dummy Load v2 (kit) | Recorded owned | DC-50 MHz; V_RMS / V_PK detector pins; ~15 W max; HF only |
| Nooelec SMA Attenuator Kit (6-piece) | Recorded owned | 1 / 2 / 3 / 6 / 10 / 20 dB. Source-listed rating: 2 W each, DC–6 GHz; rating not reverified. [Measured pads and chains](characterizations/attenuators/README.md) cover only about 1 MHz–1 GHz. |
| Generic DC-4 GHz SMA fixed attenuator board | Recorded owned | May files include PCB 0 / 10 / 20 / 30 dB captures. Exact product and mapping of physical boards to these files need confirmation. [Characterization](characterizations/attenuators/README.md). |
| BECEN SMA DC-block (x2) | Recorded owned | Source lists 50 Ω, 2 W, upper frequency 6 GHz. Lower cutoff and exact model unknown; the source phrase “DC to 6 GHz” is not a usable DC-block passband specification. |
| Crystek 2400 MHz SMA low-pass filter (x2) | Recorded owned | Source describes filters for the 2.4 GHz PA. Exact part, insertion loss and stopband measurements unknown; no measured harmonic-suppression claim imported. |
| KKnoon 150 W 20 A programmable electronic load | Recorded owned | Constant current / voltage / resistance / power, USB logging, TFT display. Drives battery discharge characterization, supply regulation tests, solar IV curves |
| Mini-Circuits BW-S30W5+ | Unconfirmed (ordered) | Older status: ordered. Arrival/current availability unconfirmed. Source-listed 30 dB, 5 W, DC–18 GHz; no matching characterization capture found. |
| Surecom SW-102 | Unconfirmed (ordered) | Older status: ordered. Arrival/current availability unconfirmed. Source-listed 125–525 MHz directional power/SWR meter. |
| RC battery wattmeter (150 A) | Recorded owned | DC only -- used for supply V / I on battery lead |
| ANENG AN8008 | Recorded owned | primary DMM |
| Uni-T DT-9205B+ | Recorded owned | second DMM, higher current range |
| Rigol DS1202Z-E | Recorded owned | 2-channel oscilloscope, 200 MHz BW, 1 GSa/s |
| Digilent Analog Discovery | Recorded owned | USB scope, logic analyzer, function generator and supply functions. Generation/model and usable limits unknown. |
| NANKADF programmable bench DC supply | Recorded owned | Used to power an HT in source notes. Exact model, output ranges and current limit unknown. |
| Pyramid PS-2230MB | Recorded owned | 30 A switching supply on Powerpole junction; runs the Icoms |

## Amplifiers and LNAs

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| WYDZ-PA-2.4-2.5GHz-10W | Listed; availability unconfirmed | Listed in source; availability unconfirmed. Source-listed 2.4–2.5 GHz, 40 dB gain, 10 W output, 28 V supply. Gain, compression, linearity and filtered output not characterized here. |
| RF2126 PA | Listed; availability unconfirmed | Listed in source; availability unconfirmed. Source-listed 400–2700 MHz and about 1 W at 2.4 GHz. Module identity and measured output/linearity unknown. |
| Generic "30-4000 MHz 40 dB" broadband module | Listed; availability unconfirmed | Listed in source; availability unconfirmed. Advertised/source range and gain only; actual bandwidth, gain and linearity unknown. |
| Nooelec SAWbird+ GOES | Listed; availability unconfirmed | Listed in source without an explicit ownership status; availability unconfirmed. Filtered LNA for the approximately 1.69 GHz receive chain; exact passband and noise figure not measured here. |
| RTL-SDR Blog wideband LNA (bias-tee powered) | Listed; availability unconfirmed | Listed in source without an explicit ownership status; availability unconfirmed. Exact model, gain, bandwidth and noise figure unknown. |
| Generic 5-3500 MHz 20 dB LNA, shielded | Listed; availability unconfirmed | Listed in source without an explicit ownership status; availability unconfirmed. Source/advertised range and gain only; noise figure and actual response unknown. |

## Radios and transceivers

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| Baofeng UV-5R | Recorded owned (x2) | Two recorded owned. 2 m / 70 cm handhelds; source reports about 1 W low / 5 W high, not a current calibrated power measurement. |
| Xiegu X6100 | Shared; current access unconfirmed | Source says loaned to Cubesat@MSU and retrievable. Current access needs confirmation before a test depends on it. |
| Icom IC-7200 | Recorded owned | HF transceiver; source-listed approximately 100 W. Present configuration and measured output unconfirmed. |
| Icom IC-9700 | Recorded owned | 2 m / 70 cm / 23 cm all-mode; model confirmed in source. Cross-band operation noted; present station configuration unconfirmed. |
| RFM95 / RFM9x LoRa modules | Recorded owned | Sub-GHz LoRa modules listed for 868 / 915 MHz. Exact variants, tuned bands and quantity unknown. |
| LoRa SX1280 module | Recorded owned | 2.4 GHz LoRa module; exact board and bring-up state unknown. |
| Lilygo T-SIM G7600 (LTE modem) | Recorded owned | Historical end-to-end link with LibreSDR, srsRAN and programmable SIM documented. Current firmware, configuration and repeatability unconfirmed. |
| Walter v1.6 (QuickSpot) | Recorded owned | ESP32-S3 + Sequans Monarch 2 GM02SP; source records LTE-M/NB-IoT/GNSS bring-up and firmware UE8.2.1.0. Current firmware/access unknown. Device identifier omitted. |
| Nordic Thingy:91X | Unconfirmed (wanted-bringup) | Source status “wanted-bringup” is ambiguous: possession and bring-up completion both need confirmation. Do not count as ready equipment. |

## SDRs

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| RTL-SDR v3 | Recorded owned | RX-only SDR. Exact unit, frequency coverage and calibration unknown; source noise-floor comparison not independently established. |
| RTL-SDR v4 | Recorded owned | RX-only SDR. Exact unit, frequency coverage and calibration unknown. |
| HackRF One | Recorded owned | Source-listed 1 MHz–6 GHz, half-duplex TX/RX, 8-bit. Board revision and measured performance unknown. |
| LibreSDR | Recorded owned | Source-listed approximately 70 MHz–6 GHz, full-duplex TX/RX. [Entry 004](../entries/004-libresdr-tx-power/README.md) records a later power check; do not generalize it to all gains/frequencies. |
| PlutoSDR | Recorded owned | Source-listed 325 MHz–3.8 GHz, full-duplex TX/RX. Any range extension/modification is unconfirmed. |

## Antennas

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| Wimo VHF X-Quad (2 m) | Recorded owned | Source reports mounted on G-5500. Current mounting, feed and polarization configuration unconfirmed. |
| Wimo UHF X-Quad (70 cm) | Recorded owned | Source reports mounted on G-5500. Current mounting, feed and polarization configuration unconfirmed. |
| Yaesu G-5500 az/el rotator | Recorded owned | Source reports satellite antenna rotation. Current controller integration and alignment unconfirmed. |
| CSN Technologies S.A.T. tracker | Recorded owned | Source describes standalone G-5500 control. Current configuration unconfirmed. |
| Backfire helix (BBQ-grill conversion) | Recorded owned | Source reports reflector with swappable 2.1 GHz and 1.7 GHz feeds and feed LNA. Beam, gain and completed receive-chain performance not characterized here. |
| 80 m HF wire antenna | Recorded owned | Source records an HF wire antenna. Installation, tuning and present condition unconfirmed. |
| J-pole (VHF / UHF) | Recorded owned | omni, omnidirectional 2 m / 70 cm |
| 2.4 GHz WiFi Yagi | Recorded owned | for ISM-band and S-band work |
| UV-5R-style extendable HT antennas | Recorded owned (several) | Several recorded owned. Exact models, count and performance unknown. |
| UHF / VHF mag-mount | Recorded owned | Previously used for balloon tracking; model and measured response unknown. |
| Small SMA "ducky" antennas | Recorded owned (assortment) | Assortment, approximately 1.5–2 inches; exact bands/models unknown. |

## Centisat hardware

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| 2S2P 18650 battery pack | Recorded owned, working | Previously recorded working for EPS. Current condition, cell details and capacity unknown. |
| EPS board (5 V + 3.3 V regulators) | Recorded owned, lightly tested | Source says both rails verified, lightly tested. Current board revision, load capability and condition unknown. |
| KKnoon electronic load | Recorded owned | Same load listed under test gear; not a second confirmed unit. |
| RP2040 + Si5351A | Unconfirmed (breadboard prototype) | Older breadboard prototype. Build state and any replacement hardware now unknown. |
| Cubesat antenna prototypes | Unconfirmed (TBD) | Testbed status unknown. [Entry 001](../entries/001-ember-antenna/README.md) separately documents EMBER copper/Nitinol prototypes; current physical availability unconfirmed. |

## LTE / cellular gear

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| LibreSDR | Recorded owned | Same SDR listed above; not another confirmed unit. Historical private LTE link documented in testbed notes. |
| Osmocom programmable SIM cards | Recorded owned | Historical G7600/srsRAN use documented. Quantity and current configuration unknown; subscriber credentials excluded. |
| Lilygo T-SIM G7600 (LTE modem) | Recorded owned | Historical end-to-end link with LibreSDR, srsRAN and programmable SIM documented. Current firmware, configuration and repeatability unconfirmed. |
| RF shielded enclosure | Unconfirmed (not really) | No verified shielded enclosure documented. Source describes a metal shop, not characterized RF isolation. Do not treat it as a shielded test fixture. |

## Computers and operating systems

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| ThinkPad X1 Carbon | Recorded owned | Source records Ubuntu/Windows dual boot and srsRAN use. Generation, CPU, RAM and present software versions unknown; source lists no discrete GPU. |
| iPad | Recorded owned | PDF reading and annotation; generation/model unknown. |

## Soldering and fabrication

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| Other Machine Co. Othermill V2 | Owned; successful wax test reported 2026-10-15; model reconfirmed 2026-10-25 | Desktop CNC mill, bought used on eBay. Mac connection, homing, PCB-bracket location and tool touch-off completed in the October 15 session; firmware reported as 101.14. See [tooling, stock and test record](#othermill-v2-tooling-and-stock). |
| Pinecil soldering iron | Recorded owned | Primary iron in source notes; version unknown. |
| KSGER SMD hot-air rework station | Recorded owned | Hot-air rework; exact model and settings/calibration unknown. |
| T-962 reflow oven | Recorded owned | Assembly oven; modifications and measured temperature profile unknown. |

### Othermill V2, tooling and stock

The 2026-10-15 conversation **“Find information about Othermill”** records the setup, owner-reported tooling and a successful wax pocket. The model label was reported as Othermill V2. These are dated inventory notes, not a new physical inspection on this page's update date.

| Tool or accessory | Recorded availability and details |
| --- | --- |
| 1/16-inch flat end mill | Installed and used for the wax test; later confirmed by the owner as solid carbide. Owner subsequently measured approximately 5 mm from the tip to where the narrow section widens. Flute count and exact part number were not physically verified; do not treat the software profile as a tool measurement. |
| 1/32-inch and 1/64-inch flat end mills | Owner-reported available; quantity, shank sizes, material and condition unrecorded. |
| Flat cutter reported as “1/18” inch | Preserve the original report pending label/diameter confirmation; do not silently substitute 1/8 inch. |
| 1/8-inch and 1/16-inch ball end mills | Owner-reported available; quantity, shank sizes, material and condition unrecorded. |
| Unidentified ball end mill | Owner measured shank at 3.13 mm and estimated cutter diameter at about 1.5 mm. Exact size/identity and whether distinct from the labeled ball cutters remain unconfirmed. |
| Engraving bits | Owner-reported assortment; angles, tip diameters and quantities unrecorded. |
| PCB-style alignment bracket | Installed; owner reported successful bracket-location routine. Earlier references to an L-bracket in the session were corrected to PCB bracket. |
| Double-sided machining tape | Available and used for wax workholding; owner reported 0.05 mm tape thickness for this setup. |

**Stock reported on hand:** assorted copper-clad PCB blanks; purple machinable wax from a chocolate-mold kit (material confirmed by the owner); multiple linoleum blocks; white plastic thought to be Delrin but unconfirmed; a red plastic block and additional purple blocks of unconfirmed material. Color alone does not identify those other plastics. The wax block used for the test measured **77.50 × 76.44 × 12.30 mm**.

**Wax test, 2026-10-15:** the owner reported “the job was successful, I ran it” and supplied a photo. The configured target was a **10 × 10 mm pocket, 0.30 mm deep**, placed 20 mm from the front and left stock edges, with a 0.05 mm tape Z offset and through-cutting disabled. The saved Bantam project confirms stock dimensions, offsets and configured engraving depth; finished pocket dimensions were not measured in the record.

The saved project records Bantam Tools **2.5.34**, a custom “Wax test - 1/16 flat” tool profile and generated cutting/plunge feeds of **950 / 40 mm/min**. The session's tool setting was 12,000 RPM, but the saved G-code requests **16,500 RPM**. This discrepancy was still unresolved at the end of the conversation; neither value is a measured spindle speed or a validated reusable cutting recipe. The successful wax cut establishes basic operation in that setup; nitinol machining was discussed but no completed nitinol cut was documented.

## Connectors and cables

| Equipment | Availability | Recorded capabilities and limits |
| --- | --- | --- |
| SMA male-male jumpers | Recorded owned (~10) | Approximately 10 in source. Calibration-grade status unknown; no specific jumper certified by this inventory. |
| Adapters (SMA / BNC / N / PL-259 / RP-SMA) | Recorded owned (assorted) | Assorted conversions; exact types, quantities and RF limits unknown. |
| LMR-400 coax | Recorded owned (many feet) | Source records many feet; installed lengths and measured loss unknown. |
| RG-58 coax | Recorded owned | Source records available coax; lengths and measured loss unknown. |
| Anderson Powerpole connectors and pigtails | Recorded owned | RC wattmeter and supply distribution |
| Alligator clip leads | Recorded owned | improvised connections |

## Software

The older inventory records Direwolf, SDR++, inspectrum, srsRAN, GNU Radio, pandoc/LuaLaTeX, SciPy/NumPy/Matplotlib, and NanoVNA-Saver/scikit-rf/pyserial as installed and used. Hosts, versions and current installations need confirmation before a test depends on a particular environment.

SigDigger, WSJT-X, fldigi, Gpredict, hamlib/rotctld, the tinySA desktop app, Wireshark/LTE dissector support, and SatDump/goestools were suggestions with installation unconfirmed. Do not count those as installed.

Bantam Tools **2.5.34** was opened and used on the Mac for the Othermill V2 wax test on 2026-10-15; the saved project also records that version. Current installation/version has not been rechecked. See the [Othermill record](#othermill-v2-tooling-and-stock) for the unresolved spindle-setting discrepancy.

## Items to confirm

- [ ] Othermill tooling: verify the cutter reported as “1/18” inch, unidentified ball cutter, exact tool/shank sizes and condition; resolve the 12,000 RPM preset versus 16,500 RPM generated-code discrepancy before reusing the wax setup.
- [ ] Mini-Circuits BW-S30W5+ and Surecom SW-102: did the older orders arrive, and are the items available?
- [ ] Thingy:91X: owned, still wanted, or waiting for bring-up?
- [ ] Xiegu X6100: current loan/access status.
- [ ] Amplifiers/LNAs: confirm availability and exact module identities; no measured gain, linearity or noise figure imported.
- [ ] Analog Discovery generation; bench supply model/output limits; ThinkPad specifications.
- [ ] NanoVNA: supported range, whether the May and October records use the same unit, and present calibration configuration. tinySA: current calibration and configuration.
- [ ] PCB attenuator identities and mapping to captures; BECEN DC-block lower cutoff and exact filter parts.
- [ ] Attenuator S11 discrepancy and zero-filled reverse parameters: see the [characterization caveats](characterizations/attenuators/README.md#limits-and-open-questions).
- [ ] 2.4 GHz attenuator measurements: absent from the May captures. Do not reuse 1 GHz-edge readings as 2.4 GHz results.
- [ ] Qualified SMA jumpers, a verified shielded enclosure, and a 1.2 GHz antenna: gaps in the older inventory, current status unknown.
- [ ] Standalone RF signal generator: listed as wanted in the testbed, but reported available in the antenna discussion. Exact model, range, output accuracy and present availability need confirmation.
- [ ] Update old Centisat prototype/build states and software installations as those items are next used.

## Source and maintenance

Seeded from `planetary_network_testbed/docs/tool_inventory.md` and `bench/pad_characterizations/`. The attenuation session is dated 2026-05-17; the older inventory has no single last-verified date. October [antenna](../entries/001-ember-antenna/README.md), [LibreSDR](../entries/004-libresdr-tx-power/README.md), and [SDRB RF](../entries/007-sdrb-rf-out/README.md) entries supply the explicitly linked updates. The Othermill update was reconciled on 2026-10-25 from the October 15 conversation “Find information about Othermill” and its saved project, `wax-first-test.btm.btp`; the owner reconfirmed the V2 model in the update request. This is a starting inventory, not an exhaustive catalog of everything owned.

Maintain this page as the shared Lab Log inventory. Update availability and exact model details when confirmed, citing the date or entry. Keep measurements with their setup and date, preserve original capture files, and distinguish source-listed ratings from measured limits. Historical entries should retain the equipment/settings actually used at the time. Device identifiers, credentials and private connection details do not belong here.

[Back to Lab Log](../README.md)
