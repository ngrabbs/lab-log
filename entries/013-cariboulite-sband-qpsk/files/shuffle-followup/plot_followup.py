"""Render the paired loss correlations for the conducted shuffle experiment."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
import subprocess
import tempfile


def export_plot(stats, output):
    pairs = defaultdict(list)
    with stats.open(newline='') as handle:
        for record in csv.DictReader(handle):
            if record['held_constant'] == 'payload' and record['phi']:
                key = int(record['symbol_rate']), record['first'], record['aligned_by']
                pairs[key].append(float(record['phi']))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        plot = root / 'paired.dat'
        with plot.open('w') as data:
            for index, rate in enumerate((250000, 500000)):
                for slot, first in enumerate(('ordered-original', 'ordered-fresh')):
                    for shift, key in [(-.15, 'sequence'), (.15, 'position')]:
                        location = 1 + slot + shift
                        values = pairs[rate, first, key]
                        for dx, value in zip((-.055, 0, .055), values):
                            data.write(f'{location+dx} {value} {key} 0\n')
                        data.write(f'{location} {mean(values)} {key} 1\n')
                data.write('\n\n')
        commands = f"""
set terminal pngcairo size 1460,720 enhanced font "Arial,16" background rgb "#ffffff"
set output "{root/'plot.png'}"
set multiplot layout 1,2 title "What moved with the failed frames?" font ",23" margins .08,.97,.17,.85 spacing .10
set border 3 lw 1.2 lc rgb "#4b5563"
set tics nomirror textcolor rgb "#374151"
set xrange [.45:2.55]
set xtics ("Original payload" 1, "Fresh payload" 2)
set xlabel "Ordered vs. shuffled pairs"
set yrange [-.35:1.05]
set ytics -.2,.2,1.0
set ylabel "Failure correlation (phi)"
set grid ytics lc rgb "#e6e9ed"
set arrow 1 from graph 0, first 0 to graph 1, first 0 nohead lw 1.5 lc rgb "#535c6b" back
set key top left font ",13"
D = "{plot}"
set title "250 ksym/s"
plot for [i=0:1] D index 0 using 1:(strcol(3) eq "sequence" && $4==i ? $2 : 1/0) with points pt (i==0 ? 7 : 5) ps (i==0 ? 1.1 : 1.7) lc rgb "#1d718e" title (i==0 ? "Aligned by sequence" : ""), \\
     for [i=0:1] D index 0 using 1:(strcol(3) eq "position" && $4==i ? $2 : 1/0) with points pt (i==0 ? 7 : 5) ps (i==0 ? 1.1 : 1.7) lc rgb "#b06727" title (i==0 ? "Aligned by position" : "")
set title "500 ksym/s"
set key off
plot for [i=0:1] D index 1 using 1:(strcol(3) eq "sequence" && $4==i ? $2 : 1/0) with points pt (i==0 ? 7 : 5) ps (i==0 ? 1.1 : 1.7) lc rgb "#1d718e" notitle, \\
     for [i=0:1] D index 1 using 1:(strcol(3) eq "position" && $4==i ? $2 : 1/0) with points pt (i==0 ? 7 : 5) ps (i==0 ? 1.1 : 1.7) lc rgb "#b06727" notitle
unset multiplot
"""
        subprocess.run(['gnuplot'], input=commands, text=True, check=True)
        output.write_bytes((root/'plot.png').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stats', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export_plot(args.stats, args.output)
