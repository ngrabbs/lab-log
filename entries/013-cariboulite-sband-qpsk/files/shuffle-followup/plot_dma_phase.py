"""Plot hard-decision bit errors within one programmed DMA period."""
import argparse
import csv
from pathlib import Path
import subprocess
import tempfile


def export_plot(stats, output):
    with stats.open(newline='') as handle:
        rows = list(csv.DictReader(handle))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        series = root / 'phase.dat'
        with series.open('w') as data:
            for rate in ('250000', '500000'):
                for row in rows:
                    if row['symbol_rate'] == rate:
                        data.write(f"{row['phase_midpoint_ms']} {float(row['ber'])*100}\n")
                data.write('\n\n')
        script = f"""
set terminal pngcairo size 1430,620 enhanced font "Arial,16" background rgb "#ffffff"
set output "{root/'phase.png'}"
set title "Bit errors folded onto the 16.384 ms transmit DMA period" font ",21"
set border 3 lw 1.2 lc rgb "#4b5563"
set tics nomirror textcolor rgb "#374151"
set xrange [0:16.384]
set yrange [0:*]
set xtics 2
set xlabel "Nominal transmit-file time within DMA period (ms)"
set ylabel "Data-field bit errors (%)"
set grid ytics lc rgb "#e6e9ed"
set key top right
D = "{series}"
plot D index 0 using 1:2 with linespoints pt 7 ps .45 lw 2 lc rgb "#1d718e" title "250 ksym/s", \\
     D index 1 using 1:2 with linespoints pt 5 ps .45 lw 2 lc rgb "#b06727" title "500 ksym/s"
"""
        subprocess.run(['gnuplot'], input=script, text=True, check=True)
        output.write_bytes((root/'phase.png').read_bytes())


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('stats', type=Path)
    cli.add_argument('output', type=Path)
    args = cli.parse_args()
    export_plot(args.stats, args.output)
