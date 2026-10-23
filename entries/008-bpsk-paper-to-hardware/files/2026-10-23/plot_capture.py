"""Plot the published sweep CSV; requires NumPy and Matplotlib. No device access."""
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

here = Path(__file__).resolve().parent
with (here / 'heartbeat-spectrum-02.csv').open() as source:
    reader = csv.reader(source)
    header = next(reader)
    rows = list(reader)
frequency = np.array([float(value) / 1e6 for value in header[4:]])
begins = np.array([float(row[2]) for row in rows])
ends = np.array([float(row[3]) for row in rows])
levels = np.array([[float(value) for value in row[4:]] for row in rows])
before = np.array([row[1] == 'before' for row in rows])
late = begins >= 2
plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none'})
fig, axes = plt.subplots(2, 1, figsize=(10, 7), layout='constrained')
fig.suptitle('EMBER conducted heartbeat: first saved burst spectrum\n2026-10-23 | TinySA input levels, external loss not added', fontsize=14)
axes[0].plot(frequency, levels[before].max(axis=0), color='#64748b', label='Idle before request: maximum of 4 sweeps')
axes[0].plot(frequency, levels.max(axis=0), color='#b45309', label='Maximum of all 44 sweeps, including burst')
axes[0].plot(frequency, levels[late].max(axis=0), color='#15803d', alpha=.65, label='Late idle: maximum after t = 2 s')
axes[0].annotate('Strongest sample\n437.0 MHz, -29.41 dBm', xy=(437, -29.40625), xytext=(438, -42), arrowprops={'arrowstyle': '->', 'color': '#b45309'})
axes[0].set(xlabel='Frequency (MHz)', ylabel='Level at TinySA input (dBm)', xlim=(430, 440), ylim=(-105, -20))
axes[0].legend(loc='upper left', fontsize=9)
index = list(frequency).index(437.)
mid = (begins + ends) / 2
axes[1].errorbar(mid, levels[:, index], xerr=(ends - begins) / 2, color='#1d4ed8', marker='o', markersize=3, linestyle='none', linewidth=.7, label='437 MHz sample; bars show sweep start/end')
axes[1].axvline(0, color='#111827', linestyle='--', linewidth=1, label='Heartbeat command written')
axes[1].set(xlabel='Time relative to heartbeat request (s)', ylabel='437 MHz input level (dBm)', ylim=(-105, -20))
axes[1].legend(loc='upper right', fontsize=9)
for ax in axes:
    ax.grid(alpha=.2)
fig.supxlabel('100 kHz RBW; 100 kHz frequency spacing; 10 dB internal attenuation; no external correction.\nSequential sweeps: this is not an occupied-bandwidth or integrated-power measurement.', fontsize=9)
destination = here.parents[1] / 'images'
destination.mkdir(exist_ok=True)
fig.savefig(destination / 'heartbeat-spectrum-02.svg')
fig.savefig(destination / 'heartbeat-spectrum-02.png', dpi=150)
