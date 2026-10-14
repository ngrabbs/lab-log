# 002 K-line payload: daylight burn and sensor linearity

**Status:** In progress
**Started:** 2026-10-14
**Updated:** 2026-10-14

Setting exposure for a daylight burn test of the three-camera narrowband payload. The session produced one solid instrument finding, one qualitative detection, and one failure: **the stored JPEGs are not linear in incident light**, the flame is clearly brightest at 770 nm, and I could not extract a trustworthy δ₇₇ against a sunlit background.

## Goal

Pick an exposure that keeps the scene unclipped, record a no-fire baseline, then measure δ₇₇ on a real flame. δ₇₇ is the potassium index: how much more light arrives at 770 nm than the two continuum bands predict.

δ₇₇ = (S₇₇₀ − C) / C, where C = (S₇₅₀ + 2·S₇₈₀) / 3

## Setup

- Raspberry Pi 4, Arducam 4-port mux, 3× InnoMaker IMX296 at 1456×1088, gain 1.0, auto-exposure off.
- Thorlabs FBH750-10 / FBH770-10 / FBH780-10. **cam0 = 770 nm (on-line), cam1 = 750, cam2 = 780.**
- Flat field `correction_20261003.npz` (Teflon panel, 3 Oct) still valid — focus, filters and resolution unchanged.
- Scene: wooden fence in late-afternoon sun, white board as a bright reference, small open flame on a bracket to its right.
- All 705 previous captures archived to `~/archive/pre_20261014/` after byte-verifying local copies, so the session started on an empty directory.

![Three narrowband views of the fence scene at 2600 µs, red marking pixels at or above 245 DN](images/scene-2600us.jpg)

The scene at 2600 µs. The bright rectangle is the white board; red marks near-saturated pixels, which appear only in 750 nm.

## The linearity finding

I bracketed to find the longest exposure with no clipping and got 2600 µs. Then the white board measured δ₇₇ = +0.135 after flat correction, which should not happen on a neutral target. That prompted a check of whether the response is linear at all.

Holding the scene static and varying exposure from 100 to 25000 µs, tracking the same pixels:

![Stored JPEG value against incident light, departing from the linear line above roughly 90 DN](images/transfer-curve.png)

Stored value against incident light for cam0 / 770 nm. The dashed line is a linear response fitted to the low-signal end.

| Incident light (linear-equivalent DN) | Stored DN | Shortfall |
| --- | --- | --- |
| 39 | 40.1 | −3% |
| 87 | 84.1 | 3% |
| 137 | 109.8 | 20% |
| 199 | 140.4 | 29% |
| 252 | 150.5 | 40% |

There is a tone curve in the image pipeline. Response is linear to roughly 55 DN, within 10% to about 87 DN, and 40% low by 250 DN. **A frame can report `clip% = 0.00` and still have its bright half badly compressed** — at 1600 µs, 4× the exposure of 400 µs gave only 2.2× the signal with nothing hard-clipped.

Two consequences:

- The working criterion is **peak ≤ 87 DN in raw values**, not "unclipped". Judge it before flat correction, since the curve acts at capture time.
- All three channels share the curve to within 1.2–1.3%, so it largely cancels in a band ratio. Where channels differ in brightness it does not fully cancel, and it compresses the brightest channel hardest.

I initially reported the 400 µs baseline as linear at 76 DN peak. That was measured after flat correction and is wrong; raw peak is 121 DN, which is marginal.

## No-fire baseline

Ten triplets at 400 µs, flat-corrected and registered. Registration was consistent to within 0.2 px across all ten: cam1 (+62.1, +132.4), cam2 (−43.8, +58.2), NCC 0.91–0.93.

| Measure | Value |
| --- | --- |
| δ₇₇, scene means | **−0.074** |
| δ₇₇, per-pixel median | −0.084 |
| p95 / p99 | +0.271 / +0.583 |
| Pixels above +0.5 | 1.51% |
| Pixels above +1.0 | 0.169% |

The last two are a **false-positive floor**. With no fire present, 1.5% of valid pixels still exceed +0.5, from registration residual on high-contrast edges and ratio noise at low signal. A detection therefore needs a contiguous region well above +1.0, not isolated hot pixels.

Only 26% of the frame is valid at 400 µs; the rest falls below the 8 DN floor where ratios become unstable. That is the cost of staying in the linear range.

Also recorded: no-fire references and dark frames at 100 / 200 / 400 / 800 µs. **Dark current is negligible** — mean 0.00005 DN, max 5 across 7.9 M pixels, matching the 24000 µs darks from 3 Oct. Dark subtraction is effectively a no-op on this sensor.

## The flame

Bracketing on the live flame, per-channel peak DN:

| Exposure | 750 | 770 | 780 | Brightest |
| --- | --- | --- | --- | --- |
| 50 µs | 31 | 20 | 26 | 750 |
| 100 µs | 50 | 43 | 50 | 750 |
| 200 µs | 80 | 58 | 88 | 780 |
| 400 µs | 133 | **147** | 118 | **770** |

At 400 µs, 770 becomes the brightest channel. On the no-fire scene it was consistently the **dimmest**. Comparing the same exposure with and without fire, 37 minutes apart:

| Band | No-fire peak | Fire peak | Increment |
| --- | --- | --- | --- |
| 750 | 125 | 133 | +8 |
| **770** | **85** | **147** | **+62** |
| 780 | 113 | 118 | +5 |

**770 gained roughly eight times what the continuum bands gained.** That channel inversion is the clearest result of the session and does not depend on how I draw a region. It is peak-based rather than integrated, taken 37 minutes apart with the sun moving, and 770 at 147 DN is compressed — which understates the gain.

![The flame in all three bands at 200 µs, identically scaled, with 770 nm visibly brightest](images/flame-three-bands.jpg)

The flame at 200 µs, aligned, identical scaling across all three. Peak above local background: 750 +24, 770 +58, 780 +49.

## What failed

I could not produce a stable integrated δ₇₇. Successive attempts gave +4.0, +0.45, −3.2, −9.0 and +2.07 on the same data, depending entirely on how the flame region and background annulus were defined. Several attempts drove the continuum estimate negative, making the ratio meaningless.

The cause is the background, not the flame. The flame is about 0.08% of the frame and sits against a sunlit fence of comparable brightness in 750 and 780. Note 780 reaches +49 against 770's +58 here, where a burn on 20 September in darkness gave 770 at six to ten times the continuum. Background structure dominates the integral.

I spent too long iterating on thresholds before looking at the frames. Rendering the flame region early would have shown the problem immediately.

## What this establishes

- The image pipeline is non-linear above roughly 90 DN. Measured, and it changes how every future exposure is chosen.
- A no-fire baseline of δ₇₇ = −0.074 with a quantified false-positive floor.
- A flame produces a large, specific 770 nm excess, visible and present in peak increments.
- **Daylight against a bright background does not yield a quantitative δ₇₇ with this method.** This was predicted in the payload documentation; it is now demonstrated.

## Next steps

Planned, not yet performed:

1. Repeat the burn **against a dark surface or at dusk**, so the flame dominates its own background. This is the single change most likely to give a measurable number.
2. Keep raw peak ≤ 87 DN on the flame itself, not the landscape.
3. Investigate raw (DNG) capture. A tone curve is irreversible at 8 bits and no calibration recovers it; this session is the strongest argument yet for a raw path.

## Files and references

- [Exposure and capture manifests](files/) — per-frame mean, p99, max and clipped fraction for every capture, with exposure. `163919` no-fire bracket, `165000` reference ladder, `165651` darks, `172754` fire bracket.
- Raw frames are held outside this repo at `payload_raw/` alongside the payload repository; they are not reproducible and want a backup.
- Payload code, calibration and analysis tools: [`koenig_wildfire`](https://github.com/ngrabbs/koenig_wildfire). Flat-field provenance in `calibration/README.md`; the 20 September detection in `docs/potassium_detection.md`.
