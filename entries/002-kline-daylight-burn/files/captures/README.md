# Original JPEG captures

These are the original JPEG files written by the payload, without later correction or alignment. They are not raw sensor data. The [main entry](../../README.md) documents the test, and the [preliminary analysis notes](../../preliminary-analysis.md) separate earlier calculations from the recorded image measurements.

A triplet contains one image from each camera. Scene labels below describe fire being present during capture, not the output of a detection algorithm.

| Folder | Setup | Scene label | Exposure | Triplets |
| --- | --- | --- | --- | ---: |
| [172824](172824/) | Sunlit fence | Fire present | 200 µs | 10 |
| [184701](184701/) | Green-painted building | Fire present | 100 µs | 15 |
| [185113](185113/) | Green-painted building, set A | Fire present | 50 µs | 15 |

Outdoor no-fire references and dark frames were also recorded. Their manifests are in the parent `files/` directory, but their original JPEGs are not included in this repository. Dark frames were taken with the lenses covered and are not outdoor no-fire examples.

## Timestamps

For example, `20261014_175138_783_cam0_770nm.jpg` records the UTC timestamp, camera port, and filter wavelength. On this test date, local US Central time was UTC−5, so 17:51:38 UTC was 12:51:38 local.

The payload Pi was set to `Europe/London`. Manifest and folder names carry that clock's offset; use the original JPEG timestamps for capture time. Both burn sessions were in daylight.

## Processing

The tools are in [koenig_wildfire](https://github.com/ngrabbs/koenig_wildfire): `tools/flat_field.py` applies the correction and `tools/register_triplets.py` aligns the images. Apply the correction before alignment: the correction map describes each camera's original pixel grid, and alignment moves those pixels.

These processing steps prepare images; they do not reproduce the reported index on their own. That also requires the exact selected area, background treatment, and averaging method, as described in the preliminary notes. Inspect the selected area over the image before accepting a flame calculation.

`correction_20261003.npz` in the parent directory was made from a Teflon panel on 3 October. Its optical configuration and exposure limitations need to be considered when using it on these captures. The earlier instruction to treat 87 DN as a verified sensor linearity limit has been withdrawn.
