# 002 Gathering daylight fire and no-fire images

**Status:** In progress

**Started:** 2026-10-14

**Updated:** 2026-10-14

Today I collected more images with the three-camera payload. My main goal was to get examples showing fire and examples without fire, record the settings, and document the measurements. For the fire tests, I burned leaves and other tree droppings, including small branches.

I used two daylight setups: a sunlit wooden fence and a green-painted building. Both produced fire images. The fence set was difficult to analyze, while one set from the building setup showed a stronger flame signal in the 770 nm view. These are useful examples for developing the processing workflow; they do not yet demonstrate reliable fire detection across different scenes.

## Equipment and setup

- Raspberry Pi 4, Arducam 4-port camera multiplexer, and three InnoMaker IMX296 monochrome cameras at 1456 × 1088 pixels.
- Filters centered at 750, 770, and 780 nm. A filter lets each camera see a narrow range of wavelengths. The 770 nm view is the channel intended to look for potassium emission; the other two provide nearby reference views.
- Camera assignment: cam0 = 770 nm, cam1 = 750 nm, cam2 = 780 nm.
- Gain set to 1.0, with automatic exposure off. Exposure is how long each camera collects light; the tables below give it in microseconds (µs).
- A white board beside the burn target provided a bright reference in both setups.
- The cameras capture one after another, with roughly two seconds from the start to the end of a three-image set. A flickering flame can change between those images.

The analysis used the existing [3 October correction file](files/correction_20261003.npz), made from images of a Teflon panel. This correction adjusts differences in brightness across the image and between cameras. Focus, filters, and resolution were reported unchanged. That does not by itself verify the correction at every exposure used today.

The measurements below are **saved JPEG pixel values**, not measurements of incoming photons or optical power. Pixel brightness is expressed on a 0–255 scale; larger values mean brighter pixels in the saved image. “DN” in the earlier notes means digital number, or pixel value.

## No-fire images and exposure checks

Before the burns, I recorded the scene without fire at several exposures. This gave reference images and a way to see how changing exposure affected saved brightness.

![Three views of the no-fire fence scene at 2600 microseconds, with near-maximum pixels marked in red](images/scene-2600us.jpg)

The white rectangle is the reference board. Red marks pixels at or above 245 out of 255. These panels show the camera views before alignment; their orientations differ.

The following table summarizes the [no-fire exposure sequence](files/bracket_20261014_165000.csv). Each entry is the average of the whole-image mean brightness from five frames in that channel. These are uncorrected JPEG values.

| Exposure | 750 nm | 770 nm | 780 nm |
| --- | ---: | ---: | ---: |
| 100 µs | 3.416 | 3.001 | 3.296 |
| 200 µs | 6.923 | 6.207 | 6.813 |
| 400 µs | 13.794 | 12.728 | 13.877 |
| 800 µs | 25.269 | 23.538 | 25.666 |

Brightness increased with exposure, but not in exactly the same proportion throughout this sequence. For example, doubling exposure from 400 to 800 µs increased the 770 nm whole-image mean by about 1.85 times. This describes the saved images in this test; it does not identify whether the cause is image processing, sensor behavior, or a change in illumination.

A bright pixel can reach the maximum saved value and lose detail; this is called clipping. Avoiding that maximum is useful, but it does not prove that saved brightness scales proportionally with exposure.

I also recorded dark frames at 100, 200, 400, and 800 µs, with the lenses covered. Those are separate from the outdoor no-fire examples. Their measurements are in the [dark-frame manifest](files/bracket_20261014_165651.csv).

## Fire test 1: sunlit fence

The first burn was against the fence, during the morning session starting around 10:30 local time. I tried several exposures while the fire was burning.

The [burn exposure manifest](files/bracket_20261014_172754.csv) records these maximum pixel values, with one frame per channel at each exposure:

| Exposure | 750 nm | 770 nm | 780 nm |
| --- | ---: | ---: | ---: |
| 50 µs | 31 | 20 | 26 |
| 100 µs | 50 | 43 | 50 |
| 200 µs | 80 | 58 | 88 |
| 400 µs | 133 | 147 | 118 |

These are the brightest pixels anywhere in each original frame, not necessarily the same point on the flame. The flame also changed between captures, so the table is a record of the images rather than a controlled comparison of flame brightness.

![Aligned close-ups of the fire against the fence in the 750, 770, and 780 nm views](images/flame-three-bands.jpg)

Processed close-ups from the 200 µs set, displayed with the same brightness scale and false color. The colors make brightness easier to see; they are not the visible colors of the flame. The fence remains prominent around the fire.

The initial analysis could not produce a dependable flame index from this set. Changing the selected flame area and the nearby area used to estimate background gave very different answers. I am keeping the images as fire examples, but not treating that calculation as a reliable result.

## Fire test 2: green-painted building

The second setup was in front of a green-painted building, during the session starting around 12:45 local time. I used the same cameras and filters, recording a 100 µs set and two 50 µs sets.

![Processed three-channel views of two 50 microsecond sets against the building, with selected areas outlined in white](images/green-building-flame.jpg)

Each panel averages 15 frames and uses the same display scale. In the top row, set A, the outline covers the flame and the 770 nm view is visibly brighter there. In the bottom row, set B, the automatically selected area covers the board edge and another object rather than the flame. Set B is excluded from the flame-index result; it is not a verified no-fire example.

Both tests took place in daylight. An earlier version incorrectly called the second test an evening session. The short exposures made the background look dark, and the payload clock was mistaken for local time.

For [set A at 50 µs](files/bracket_20261014_185113.csv), the largest pixel value across all 15 original frames in each channel was:

| Channel | Maximum JPEG pixel value |
| --- | ---: |
| 750 nm | 62 |
| 770 nm | 83 |
| 780 nm | 83 |

These are whole-frame maxima. They are different from measurements restricted to the outlined flame area, and do not establish a sensor linearity limit.

This set gave a more useful flame comparison than the fence set. However, the time, exposure, flame, and analysis choices also differed. The images do not isolate the background as the only reason for the difference.

## Results and current limits

The session added daylight examples with and without fire, along with recorded exposure settings and image-brightness measurements. The fire examples came from burning leaves and small branches. One building set showed a stronger 770 nm signal in the selected flame area; the fence set did not give a dependable index with the analysis tried.

An earlier analysis reported a derived index of δ₇₇ = +2.49 for the building set at 50 µs. The [preliminary analysis notes](preliminary-analysis.md) retain that result and explain what was calculated. It is a result of a particular processing method and selected area, not a calibrated measurement of potassium emission.

## Files and references

A triplet is one image from each of the three cameras. The folders below contain original JPEG captures; the image panels above are processed summaries.

| Record | Scene label | Exposure | Triplets | Available here |
| --- | --- | --- | ---: | --- |
| [No-fire exposure sequence](files/bracket_20261014_165000.csv) | No fire present | 100 / 200 / 400 / 800 µs | 5 per exposure | Measurements; original JPEGs not included |
| [Dark-frame sequence](files/bracket_20261014_165651.csv) | Lenses covered | 100 / 200 / 400 / 800 µs | 5 per exposure | Measurements; original JPEGs not included |
| [Fence set](files/captures/172824/) | Fire present | 200 µs | 10 | Original JPEGs and [manifest](files/bracket_20261014_172824.csv) |
| [Building set](files/captures/184701/) | Fire present | 100 µs | 15 | Original JPEGs |
| [Building set A](files/captures/185113/) | Fire present | 50 µs | 15 | Original JPEGs and [manifest](files/bracket_20261014_185113.csv) |

The full day's captures are held outside this repository in `payload_raw/` alongside the payload repository. See the [capture notes](files/captures/README.md) for timestamps and processing details, and [koenig_wildfire](https://github.com/ngrabbs/koenig_wildfire) for the payload code and analysis tools.
