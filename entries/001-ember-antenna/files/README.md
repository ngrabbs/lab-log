# Measurement files

Instrument captures from October 7 and 8, 2026. Times below are America/Chicago; source timestamps were UTC.

Each folder contains the original CSV, available Touchstone S11, and raw console replies for S11, frequencies, sweep, and calibration. Screen captures are in the entry image folder. Derived CSV quantities use a 50 Ω reference. Screen and numerical data were acquired sequentially during live sweeps, so they can differ slightly.

| Capture | Local time | Configuration |
| --- | --- | --- |
| [nitinol-narrow](nitinol-narrow/sweep.csv) | 2026-10-07 16:56:30 | Nitinol on spacecraft, initial narrow sweep; earlier calibration |
| [nitinol-coax-down](nitinol-coax-down/sweep.csv) | 2026-10-07 17:01:59 | Nitinol with coax routed down; selected baseline; earlier calibration |
| [nitinol-extended](nitinol-extended/sweep.csv) | 2026-10-07 17:04:47 | Ribbons pulled farther out of clamps, total lengths unchanged; earlier calibration |
| [nitinol-coax-top](nitinol-coax-top/sweep.csv) | 2026-10-07 17:07:10 | Coax across spacecraft top; earlier calibration |
| [load-recal-narrow](load-recal-narrow/sweep.csv) | 2026-10-07 17:35:45 | Load consistency check after narrow SOL recalibration |
| [load-cal4-wide](load-cal4-wide/sweep.csv) | 2026-10-07 19:04:43 | Load-like check after user reported 300–500 MHz SOL in slot 4 |
| [nitinol-cal4](nitinol-cal4/sweep.csv) | 2026-10-07 19:05:53 | Nitinol on raised plastic jig after wide SOL calibration |
| [copper-hanging](copper-hanging/sweep.csv) | 2026-10-07 19:42:02 | Preliminary copper supported from soldering station, before holder |
| [copper-holder](copper-holder/sweep.csv) | 2026-10-08 06:42:56 | 170 mm copper arms installed in holder, original exposed feed |
| [copper-open-feed](copper-open-feed/sweep.csv) | 2026-10-08 06:59:15 | Shortened feed and relocated clamps, failed connection; not valid tuning data |
| [copper-repaired-170](copper-repaired-170/sweep.csv) | 2026-10-08 07:20:33 | Antenna-side center termination repaired, 170 mm copper baseline |
| [copper-trim-168](copper-trim-168/sweep.csv) | 2026-10-08 07:24:17 | Copper arms approximately 168 mm, fixed repaired feed and holder |
| [copper-trim-166](copper-trim-166/sweep.csv) | 2026-10-08 07:26:13 | Copper arms approximately 166 mm, fixed repaired feed and holder |
| [copper-trim-164](copper-trim-164/sweep.csv) | 2026-10-08 07:27:50 | Copper arms approximately 164 mm, fixed repaired feed and holder |
| [copper-trim-162](copper-trim-162/sweep.csv) | 2026-10-08 07:32:10 | Copper arms approximately 162 mm, fixed repaired feed and holder |
| [copper-trim-160](copper-trim-160/sweep.csv) | 2026-10-08 07:49:44 | Copper arms approximately 160 mm, fixed repaired feed and holder |

The repaired-feed source notes initially left calibration equivalence unresolved. The subsequent experiment discussion confirmed that only the antenna-side termination was repaired and the calibrated cable/fittings were unchanged.

Earlier calibration and setup captures are retained as history. They should not be pooled with the C4 trimming sequence as one controlled dataset. The copper hanging, copper holder, and Nitinol arrangements also differ in geometry.

The failed open-feed capture includes reflection magnitudes slightly above unity, yielding nonphysical derived values such as infinite VSWR or negative resistance. Retain it as a fault record; do not interpret it as antenna gain or use it for tuning.
