"""Plot transmit-period bit errors before and after the SMI callback fix."""
import argparse
import csv
from pathlib import Path
import subprocess
import tempfile


def plot(table, output):
    with table.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        data = root/'phase.dat'
        with data.open('w') as handle:
            for rate in ('250000','500000'):
                for stage in ('before', 'after'):
                    for row in rows:
                        if (row['stage'], row['symbol_rate']) == (stage, rate):
                            handle.write(f"{row['phase_center_ms']} {100*float(row['ber'])}\n")
                    handle.write('\n\n')
        commands = f"""
set terminal pngcairo size 1450,670 enhanced font "Arial,16" background rgb "#ffffff"
set output "{root/'plot.png'}"
set multiplot layout 1,2 title "TX DMA boundary before and after the callback fix" font ",22" margins .078,.969,.17,.85 spacing .11
set border 3 lw 1.2 lc rgb "#4b5563"
set tics nomirror textcolor rgb "#374151"
set xrange [0:16.384]
set yrange [0:8]
set xtics 4
set xlabel "Time within the 16.384 ms TX DMA period (ms)"
set ylabel "Data-field bit errors (%)"
set grid ytics lc rgb "#e6e9ed"
set key top right
D = "{data}"
set title "250 ksym/s"
plot D index 0 using 1:2 with linespoints pt 7 ps .45 lw 2 lc rgb "#a25a31" title "Old driver", \\
     D index 1 using 1:2 with linespoints pt 5 ps .45 lw 2 lc rgb "#1d718e" title "Patched driver"
set title "500 ksym/s"
set key off
plot D index 2 using 1:2 with linespoints pt 7 ps .45 lw 2 lc rgb "#a25a31" notitle, \\
     D index 3 using 1:2 with linespoints pt 5 ps .45 lw 2 lc rgb "#1d718e" notitle
unset multiplot
"""
        subprocess.run(['gnuplot'], input=commands, text=True, check=True)
        output.write_bytes((root/'plot.png').read_bytes())


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('table',type=Path)
    cli.add_argument('image',type=Path)
    args=cli.parse_args()
    plot(args.table,args.image)
