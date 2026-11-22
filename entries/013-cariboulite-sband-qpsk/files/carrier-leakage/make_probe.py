"""Make the 2 MS/s zero-IQ and signed-tone conducted probe."""
import sys
import numpy as np

period = 524288
amplitude = 12000
indices = np.arange(period)
sections = []
for frequency in (None, 200000, None, -200000, None):
    if frequency is None:
        sections.append(np.zeros((period,2),dtype='<i2'))
    else:
        z = amplitude*np.exp(2j*np.pi*frequency/2_000_000*indices)
        sections.append(np.rint(np.column_stack((z.real,z.imag))).astype('<i2'))
np.concatenate(sections).tofile(sys.argv[1])
