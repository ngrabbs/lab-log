# Components on hand and recorded orders

**Organized:** 2026-11-10. Imported from the owner's existing electronics inventory; this was not a new physical count.

Use this page when choosing parts already available for a build. [Equipment](../equipment/README.md) covers instruments and reusable lab tools; [toroid stock](toroids.md) covers the separate core assortment. Project headings below are recorded associations, not proof that parts are reserved, installed, or unavailable to other projects.

## How to interpret the records

- **Recorded on hand / arrived:** the source note lists possession. Current remaining quantity and condition have not been recounted.
- **Recorded order:** receipt is unconfirmed. Do not select it as an available part merely because the order is old.
- **Recorded qty:** copied from the source. “Several,” “—,” lot sizes, and assortment counts are not exact remaining stock. Kit piece counts may be original contents, not a current count.
- Descriptions, ratings, and package information are inherited from the source, not newly checked specifications. Follow manufacturer documentation for a design that depends on them.
- Storage/bin locations were not recorded. Add them when sorting rather than inventing them.
- Do not sum potentially overlapping kit contents, general entries, or ambiguous module identities.

## Recorded arrived — identification and sorting pending

The source arrival list gives these part numbers and quantities without descriptions or project allocation. Keep the exact markings until identified.

| Part | Recorded qty | Status |
| --- | --- | --- |
| 600F330JT250XT4K | 5 | Recorded arrived; needs sorting |
| C0805C100JDGACTU | 5 | Recorded arrived; needs sorting |
| 600F470JT250XT4K | 5 | Recorded arrived; needs sorting |
| 600F150FT250XT4K | 5 | Recorded arrived; needs sorting |
| QSCT1251Q680J1GV001E | 5 | Recorded arrived; needs sorting |
| 600F6R8CT250XT4K | 5 | Recorded arrived; needs sorting |

The arrived ADE-1+, MCP6022T-I/SN, and SN74LVC1G86DBVR batches are listed once under Centisat below. Their earlier order rows have been superseded, not added to their arrival quantities.

## Recorded orders — receipt unconfirmed

### General Supplies
| Part | Description | Recorded qty | Source | Notes |
|------|-------------|-----|--------|-------|
| Kester "44" 63/37 0.015" | Rosin-core solder | 1 | Amazon | [link](https://www.amazon.com/Kester-Rosin-Core-Solder-Dispense-Pak/dp/B017WK9HQS/) |
| SMD inductor kit | Assortment | 1 | AliExpress | [link](https://www.aliexpress.us/item/3256804082345431.html) |
| IMX678 camera w/ 150x zoom | Imaging sensor + lens | 1 | AliExpress | [link](https://www.aliexpress.us/item/3256811813182644.html) |
| DC-DC buck modules | Step-down converters | 1 lot | AliExpress | [link](https://www.aliexpress.us/item/3256808492415082.html) |

### Pico Breadboard Radio
| Part | Description | Recorded qty | Source | Notes |
|------|-------------|-----|--------|-------|
| 1699-ND | 3.5mm stereo jack | 1 | Digi-Key | |

### Centisat Comms Board
| Part | Description | Recorded qty | Source | Notes |
|------|-------------|-----|--------|-------|
| NE612AD | Double-balanced mixer & oscillator, SOP-8 | — | eBay (Signetics) | |
| SPF5189Z | RF LNA IC | 10 | eBay | |
| SA612A | Mixer/oscillator, SOP-8 | 5 | eBay | Older note said “Expected Monday”; date and receipt unconfirmed |

---

## Recorded on hand — project-associated parts

### Pico Breadboard Radio
| Part | Description | Recorded qty | Notes |
|------|-------------|-----|-------|
| MCP6022-E/P | Dual op-amp, DIP-8 | 1 | Digi-Key MCP6022-E/P-ND |
| SN74CBTLV3253PWR | 2x 4:1 mux/demux, TSSOP-16 | 1 | Digi-Key 296-9133-1-ND |
| Rotary encoder | | 1 | Digi-Key 1528-2438-ND |
| ADA 2202 | 8-pin 0.3" IC socket | — | Adafruit |
| ADA 1212 | SOIC-8 / MSOP-8 / TSSOP-8 SMT breakout PCB | — | Adafruit |
| ADA 1207 | SOIC-16 / TSSOP-16 SMT breakout PCB | — | Adafruit |
| ADA 590 | Perma-Proto full-size breadboard PCB | — | Adafruit |
| ADA 4863 | Raspberry Pi Pico (RP2040) | — | Adafruit |

### Centisat Comms Board
The arrival list supersedes the old “no delivered parts yet” note. These are the same batches previously listed on order, counted once; they were recorded arrived and still need physical sorting. Project association comes from the original order section.

| Part | Description | Recorded qty | Source | Status |
| --- | --- | --- | --- | --- |
| SN74LVC1G86DBVR | Single XOR gate | 10 | Digi-Key | Recorded arrived; needs sorting |
| MCP6022T-I/SN | Dual op-amp, SOIC-8 | 5 | Digi-Key | Recorded arrived; needs sorting |
| ADE-1+ | Mini-Circuits passive mixer | 2 | Digi-Key | Recorded arrived; needs sorting |

### PowerFilm Oscillator
| Part | Description | Recorded qty | Notes |
|------|-------------|-----|-------|
| SP3-37 | PowerFilm flexible solar cell | 2 | |
| MPT3.6-75 | PowerFilm flexible solar cell | 1 | |

---

## Recorded on hand — general inventory

### Microcontrollers & Dev Boards
| Part | Package / Form | Recorded qty | Notes |
|------|----------------|-----|-------|
| ATmega328P | DIP-28 | 12 | Arduino-compatible, pre-flashed bootloader, 1.8–5.5V |
| ESP32-WROOM-32 | QFN-38 (on dev boards) | 6 | WiFi/BLE SoC, 3.0–3.3V |
| RP2040 | QFN-56 | 10 | PIO support for custom protocols, 1.8–3.3V |
| STM32F103C8T6 | TQFP-48 (Blue Pill) | 5 | ARM Cortex-M3, 2.0–3.6V |
| Raspberry Pi Pico / Pico W | RP2040 dev board | several | Basic dev boards w/ and w/o WiFi |
| Adafruit RP2040 Feather | Feather form factor | 3 | Feather ecosystem compatible |
| Adafruit KB2040 | Pro Micro–style RP2040 w/ USB-C | 1 | |
| Pi Zero 2 W | Raspberry Pi SBC | 2 | Compact Linux SBC |

### Sensors
| Part | Interface | Recorded qty | Notes |
|------|-----------|-----|-------|
| BMP280 (HW-611 marking) | I2C / SPI | several | Recorded as Bosch pressure + temperature breakout; may overlap the unidentified HW-611 row below. |
| INA219 (HiLetgo breakout) | I2C | 9 | DC voltage / current / power monitor |
| LC709203 (StemmaQT breakout) | I2C | 1 | Li-Ion fuel gauge, JST + StemmaQT headers |
| HW-611 (?) | TBD | several | Unknown module; may be the BMP280 batch above. Do not add the two quantities until identified. |

### Power — Regulators
| Part | Package | Recorded qty | Notes |
|------|---------|-----|-------|
| AMS1117-1.2V | SOT-223 | 10 | |
| AMS1117-1.5V | SOT-223 | 10 | |
| AMS1117-1.8V | SOT-223 | 10 | |
| AMS1117-2.5V | SOT-223 | 10 | |
| AMS1117-3.3V | SOT-223 | 10 | |
| AMS1117-5.0V | SOT-223 | 10 | |
| AMS1117-ADJ | SOT-223 | 10 | |
| LM317 | TO-220 | 5 | Adjustable linear regulator |
| LM25116MHX/NOPB | HTSSOP-20 | 2 | High-voltage synchronous buck controller |
| TPSM5D1806RDBR | B0QFN | 1 | TI 6A synchronous buck power module, integrated inductor |

### Power — Boost / Charger Modules
| Part | Form | Recorded qty | Notes |
|------|------|-----|-------|
| XL6009 module | Power module | 4 | DC-DC boost converter |
| MT3608 | Power module | 10 | Small adjustable boost converter |
| PowerBoost 500 (Adafruit) | Breakout | 1 | TPS61090 USB-rechargeable boost |
| PowerBoost 500 Basic (Adafruit) | Breakout | 4 | Bare-bones TPS61090 |
| PowerBoost 1000 Basic (Adafruit) | Breakout | 2 | High-current USB boost |
| Adroit USB MicroLipo | MicroUSB charger | 1 | 3.7V LiPo charger |
| Adafruit MCP73871 board | Charger board | 1 | USB/solar Li-Ion charger w/ power-path mgmt |
| LTC4162EUFD-LADM#PBF | QFN-28 | 1 | Linear Tech advanced multi-chemistry buck battery charger w/ I²C / telemetry |
| friedcircuits.us USB test board | USB inline | 1 | USB-A → microUSB current/voltage monitor |

### Power — Solar
| Part | Description | Recorded qty | Notes |
|------|-------------|-----|-------|
| AK72X45 | ~72×45 mm low-cost PV panels | 10+ | Basic efficiency |

### Diodes
| Part | Package | Recorded qty | Notes |
|------|---------|-----|-------|
| IN34A | DO-7 | 25 | Germanium, low Vf, RF detection |
| 1N60 | Glass DO-7 | 100 | Germanium, radio signal detection |

### Transistors
| Part | Type | Package | Recorded qty | Notes |
|------|------|---------|-----|-------|
| TIP120 | NPN Darlington | TO-220 | 5 | Drives up to 5A, good for motors |
| TIP3055 | NPN power | TO-218 | 3 | 15A / 60V general-purpose power transistor |
| BD139 | NPN power | TO-126 | 5 | General-purpose high-current NPN |

### Logic & Mixed-Signal ICs
| Part | Package | Recorded qty | Notes |
|------|---------|-----|-------|
| SN74HC595N (BOJACK) | DIP-16 | 25 | 8-bit 3-state shift register |
| 4N35-ND | DIP-6 | 10 | Optocoupler, phototransistor output |
| MCP4822-E/P | DIP-8 | 2 | Dual 12-bit SPI DAC, voltage out |
| 74HCxx logic IC kit | DIP-14/16 | 30 types | AND/OR/NOT, flip-flops, latches, shift regs, muxes |

### Op-Amps, Comparators, Timers
| Part | Package | Recorded qty | Notes |
|------|---------|-----|-------|
| Op-amp / comparator assortment | DIP-8 | 161 | LM358, LM324, UA741, NE5532, etc. |
| Logic / timer / opto assortment | DIP-8/14/16 | 161 | NE555, PC817, UC3842, CD4047, etc. |

### RF / Analog Misc
| Part | Form | Recorded qty | Notes |
|------|------|-----|-------|
| CRB 455E | Through-hole | 20 | 455 kHz ceramic resonator (IF stages) |
| 0805CS-150XJRC | Coilcraft inductor, 0805 | 5 | 15 nH air-core |
| 0805CS-220XJRC | Coilcraft inductor, 0805 | 5 | 22 nH air-core |
| 0805CS-560XJRC | Coilcraft inductor, 0805 | 5 | 56 nH air-core |
| 0805CS-121XJRC | Coilcraft inductor, 0805 | 5 | 120 nH air-core |

### Passive Component Kits
| Kit | Contents | Recorded qty | Notes |
|-----|----------|-----|-------|
| 0805 SMD assortment kit | Resistors, caps, inductors, LEDs, transistors, ICs, basic op-amps/timers | 5435 pcs | Includes tools |
| Electrolytic capacitor kit | 24 values, 0.1 µF–1000 µF, radial | 500 | Filtering / bypass |
| Ceramic cap kit (10×50) | 10 values, 0.1–10 µF, 50V | 500 | Yellow dipped |
| Ceramic cap kit (BOJACK 15×40) | 15 values, 10 pF–100 nF | 600 | Signal coupling / bypass |
| Trimpot kit | 15 values, 100 Ω–1 MΩ, through-hole | 150 | Precision tuning |
| Inductor kit (BOJACK 20×10) | 20 values, axial, 1 µH–1 mH, ½ W | 200 | Color-coded |
| DIP switch assortment | 2–12 position slide-style | ~30 | Mode/config toggling |

### Connectors / Misc
| Part | Description | Recorded qty | Notes |
|------|-------------|-----|-------|
| Screw terminals | PCB-mount screw terminal blocks | — | Amazon B0GF83Y476 |

## Reconciliation and maintenance

- [ ] Check which recorded orders arrived; move each batch into the appropriate on-hand section, retaining its source and recording the confirmation date.
- [ ] Sort the six unidentified arrived part numbers and add descriptions, packages, and storage locations.
- [ ] Sort the three arrived Centisat batches and confirm remaining quantities.
- [ ] Identify the HW-611 modules before treating the two sensor rows as distinct stock.
- [ ] Record toroid quantities and storage locations in [toroid stock](toroids.md).

Keep one inventory row per known batch. Update remaining quantity when consumed or reserved; keep the experiment's actual part choice and measurements in its project/lab entry. Add a date/source to confirmations and distinguish label/listing specifications from measured behavior.

Source: the owner's pre-existing electronics inventory, reorganized November 10, 2026. The underlying note had no single physical-inventory date. No equipment was purchased, tested, or newly counted during this cleanup.

[Equipment](../equipment/README.md) · [Toroid stock](toroids.md) · [Lab Log](../README.md)
