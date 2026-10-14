# Source captures

Raw frames as written by the payload, unmodified. Provided so the results in
the parent entry can be reproduced independently.

| Folder | Session | Exposure | Triplets | What it shows |
| --- | --- | --- | --- | --- |
| `172824/` | 1, bright fence | 200 µs | 10 | The case that could **not** be measured |
| `184701/` | 2, green building | 100 µs | 15 | 770 nm above the linear limit; the median-vs-mean comparison |
| `185113/` | 2, green building | 50 µs | 15 | **The result: δ₇₇ = +2.49** |

## Filename convention

```
20261014_175138_783_cam0_770nm.jpg
└── UTC timestamp ──┘ └cam┘ └band┘
```

**Timestamps are UTC.** The payload Pi is set to `Europe/London`, so its
displayed clock is not local time and the bracket manifest filenames carry
that offset. Local time at the test site was UTC−5 (US Central). The frame
stems are the reliable record: `175138` UTC is 12:51 local.

## Reproducing

Tools are in [`koenig_wildfire`](https://github.com/ngrabbs/koenig_wildfire).
Apply the flat field **before** registration — the gain map is tied to the
sensor's pixel grid and registration warps the frame.

```bash
tools/flat_field.py apply ./185113 --correction ../correction_20261003.npz -o ./corrected
tools/register_triplets.py ./corrected -o ./aligned --no-crop
```

Then integrate over the flame region. Two things materially affect the answer:

- **Average frames with the mean, not the median.** A median rejects a
  flickering flame as an outlier; see the comparison in the parent entry.
- **Check the raw peak stays at or below 87 DN.** Above that the sensor's
  stored values are compressed and the on-line channel is suppressed most.

`correction_20261003.npz` in the parent `files/` directory is the flat field
used here, from a Teflon panel on 3 Oct. It is valid only for this optical
configuration.
