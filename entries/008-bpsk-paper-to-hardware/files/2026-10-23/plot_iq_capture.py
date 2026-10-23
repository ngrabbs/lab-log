"""Plot published IQ-derived CSVs; NumPy/Matplotlib only, no device access."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

here = Path(__file__).resolve().parent
metadata = json.loads((here / 'iq-heartbeat-01-session.json').read_text())
with (here / 'iq-heartbeat-01-power.csv').open() as source:
    rows = list(csv.DictReader(source))
time = np.array([float(row['seconds_from_capture_start']) for row in rows])
power = np.array([[float(row[f'ch{ch}_mean_iq_power']) for row in rows] for ch in (0, 1)])
with (here / 'iq-heartbeat-01-preamble.csv').open() as source:
    rows = list(csv.DictReader(source))
coarse = np.array([complex(float(row['coarse_cfo_real']), float(row['coarse_cfo_imag'])) for row in rows])
states = np.array([int(row['state']) for row in rows])
symbol_times = np.array([int(row['preamble_symbol_index']) / 1200 for row in rows])
initial_centers = np.array([coarse[states == state].mean() for state in (0, 1)])
common_phase = np.unwrap(np.angle(coarse * np.conj(initial_centers[states])))
slope, _ = np.polyfit(symbol_times, common_phase, 1)
points = coarse * np.exp(-1j * slope * symbol_times)
exported = np.array([complex(float(row['refined_cfo_real']), float(row['refined_cfo_imag'])) for row in rows])
if not np.allclose(points, exported, rtol=1e-10, atol=1e-12):
    raise ValueError('CSV frequency refinement does not reproduce')
centers = np.array([points[states == state].mean() for state in (0, 1)])
normalization = np.exp(-1j * np.angle(centers[0])) / abs(centers[0])
points *= normalization
centers *= normalization
separation = metadata['preamble_frequency_refinement']['separation_deg']
plt.rcParams.update({'font.size': 10, 'svg.fonttype': 'none'})
fig, axes = plt.subplots(1, 2, figsize=(11, 5), layout='constrained')
fig.suptitle('One conducted heartbeat: receiver path and preamble phase\n2026-10-23 | 437 MHz tuning, 192 ksample/s, gain 0 dB', fontsize=14)
for channel, color in [(0, '#1d4ed8'), (1, '#b45309')]:
    axes[0].plot(time, 10 * np.log10(power[channel]), color=color, label=f'UHD channel {channel}')
axes[0].set(xlabel='Time from capture start (s)', ylabel='10 log10(mean |IQ|²), relative digital units', xlim=(67.7, 69.5))
axes[0].legend(loc='upper right')
axes[0].grid(alpha=.2)
theta = np.linspace(0, 2 * np.pi, 300)
axes[1].plot(np.cos(theta), np.sin(theta), color='#cbd5e1', linewidth=1)
axes[1].axhline(0, color='#cbd5e1', linewidth=.6)
axes[1].axvline(0, color='#cbd5e1', linewidth=.6)
for state, color in [(0, '#1d4ed8'), (1, '#b45309')]:
    values = points[states == state]
    axes[1].scatter(values.real, values.imag, s=12, alpha=.6, color=color, label=f'Preamble state {state}')
    axes[1].plot([0, centers[state].real], [0, centers[state].imag], color=color, linewidth=1.5)
    axes[1].scatter([centers[state].real], [centers[state].imag], marker='x', s=75, color='#111827')
axes[1].scatter([-1], [0], marker='+', s=90, color='#64748b', label='Ideal antipodal reference')
axes[1].text(-.1, -.8, f'Measured centers: {separation:.1f}° apart\nIdeal BPSK: 180°', ha='center')
axes[1].set(xlabel='Normalized I', ylabel='Normalized Q', xlim=(-1.4, 1.4), ylim=(-1.2, 1.4), aspect='equal')
axes[1].legend(loc='upper right', fontsize=8)
fig.supxlabel('Phase panel: 248 known preamble symbols, central 8/40 samples, one common frequency refinement.\nA single global rotation/scale sets state 0 to unity; states are not forced antipodal. No BER is inferred.', fontsize=9)
destination = here.parents[1] / 'images'
fig.savefig(destination / 'iq-heartbeat-01.svg')
fig.savefig(destination / 'iq-heartbeat-01.png', dpi=150)
