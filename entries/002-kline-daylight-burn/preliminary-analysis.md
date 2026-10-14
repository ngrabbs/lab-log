# Preliminary analysis: 14 October daylight captures

These notes retain calculations reported in the first write-up. They are separate from the [image-gathering log](README.md) because they depend on processing choices and need further checking. The tables below are earlier reported analysis results, not new independent measurements or a reproduction of the original analysis.

## What the index means here

The processing compares the 770 nm channel with a reference estimated from the 750 and 780 nm channels:

```text
C = (S750 + 2 × S780) / 3
δ77 = (S770 − C) / C
```

S is the summed processed pixel value in a selected area. A positive index means the processed 770 nm total exceeds that weighted reference. It does not, by itself, prove that potassium caused the difference. The calculation is meaningful only when the reference is positive and large enough for a stable comparison.

Images were corrected using `correction_20261003.npz` and aligned so the channels could be compared over a common area. The [calibration notes](https://github.com/ngrabbs/koenig_wildfire/blob/main/calibration/README.md) describe the correction's source and limitations, including unreliable gains near the outer edge of the field. This is a panel-based relative correction, not an absolute photon calibration.

## No-fire baseline

The first analysis reported these results for ten triplets at 400 µs:

| Quantity | Reported value |
| --- | ---: |
| Index calculated from scene means | −0.074 |
| Median pixel index | −0.084 |
| 95th / 99th percentile pixel index | +0.271 / +0.583 |
| Valid pixels with index above +0.5 | 1.51% |
| Valid pixels with index above +1.0 | 0.169% |
| Fraction of frame retained by the 8 DN signal cutoff | 26% |

These figures describe that scene and processing method. They do not establish a general detector false-positive rate or a validated detection threshold. The original no-fire JPEGs and exact analysis inputs are not included here.

The earlier claim that this baseline was within a verified linear range is withdrawn. A corrected pixel value cannot be used as the original capture brightness; the no-fire exposure manifest includes uncorrected maxima above the earlier proposed 87 DN cutoff.

## Fence calculation

The earlier analysis reported indices of +4.0, +0.45, −3.2, −9.0, and +2.07 when changing the selected flame and background areas. Some choices produced a negative reference after background subtraction. Those calculations are not accepted flame measurements.

The fence was prominent in the images, making background separation a plausible difficulty. This does not establish that the background was the sole cause of the unstable calculations.

## Building: averaging choices at 100 µs

For the [100 µs building set](files/captures/184701/), the earlier write-up reported:

| Frames combined using | S750 | S770 | S780 | Index |
| --- | ---: | ---: | ---: | ---: |
| Median at each pixel | 13.7k | 15.0k | 11.5k | +0.222 |
| Mean at each pixel | 14.5k | 28.1k | 14.3k | +0.957 |

The values are rounded summed processed pixel values; “k” means thousand. A mean averages all sampled values. A median takes the middle value and can reduce an intermittent flame's contribution at a pixel. This comparison shows that the choice mattered for this set; neither output is calibrated optical flux.

The 750 and 780 nm totals in the mean row differ by about 1.4% of their average. That observation belongs to this 100 µs set, not the 50 µs result below.

## Building set A at 50 µs

For [set A](files/captures/185113/), using the mean of 15 frames, the earlier analysis reported:

| Channel | Summed processed pixel value in the selected area |
| --- | ---: |
| 750 nm | 5.4k |
| 770 nm | 25.9k |
| 780 nm | 8.4k |

| Quantity | Reported value |
| --- | --- |
| Combined-set index | +2.49 |
| Median of the 15 individual triplet indices | +3.40 |
| Individual triplet range | −0.24 to +5.09 |
| Triplets with a positive index | 93% |
| Selected area | 6337 pixels |

The displayed rounded totals give an index of about +2.50. The earlier +2.49 value is retained as reported; exact totals and the analysis script are needed to check it. The 750 and 780 nm totals are not within 1.4% here: 8.4k is about 56% greater than 5.4k.

The [manifest](files/bracket_20261014_185113.csv) gives a maximum original JPEG value of 83 in the 770 nm channel. That verifies the recorded whole-frame maximum, not a claim that the sensor or selected area is “fully linear.” The earlier selected-area peak table has been omitted because its processing stage and measurement area were not documented precisely enough to compare with the manifest.

Set B's selected area covered other objects rather than the flame. Its earlier reported +0.37 is excluded from the flame result. It should not be labeled no-fire solely because the area selection failed.

## Exposure-response interpretation

The first write-up also reported a sweep from 100 to 25000 µs, using a fitted low-brightness response to construct a [comparison plot](images/transfer-curve.png). That historical plot labels its horizontal axis “incident light,” but it is an estimated linear-equivalent pixel scale, not an independently measured incident-light scale. The exact fit, sampled pixels, and generating script are not included here, so the plot is not used as an established calibration result.

The claims of a specific tone curve, a universal 87 DN linearity cutoff, cancellation of nonlinear response in channel ratios, and the 100 µs index being a guaranteed lower bound are withdrawn pending verification. The exposure-versus-JPEG measurements in the main entry are the directly documented result.

## What is needed to reproduce the derived results

The original JPEGs and correction file are included for the three fire sets. To reproduce the indices exactly, the record also needs the analysis script or commands, alignment settings, saved area masks, background-subtraction method, exact channel totals, and per-triplet results. The correction's behavior at these exposures also needs checking.

The sequential captures allow the flame to change between channels. This session does not document a comparable unfiltered response test, an absolute incident-light measurement, or a conversion from pixel values to photons. Until those limits are addressed, these indices remain preliminary comparisons of processed images.
