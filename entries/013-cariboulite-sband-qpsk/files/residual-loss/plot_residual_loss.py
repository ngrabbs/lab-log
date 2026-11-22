"""Plot error location and packet loss for the same-IQ receiver replay."""
import argparse
import csv
from pathlib import Path
import subprocess
import tempfile


def plot(source, target):
    with (source/'bit-errors-by-decile.csv').open(newline='') as handle:
        bits = list(csv.DictReader(handle))
    with (source/'replay-by-rate.csv').open(newline='') as handle:
        runs = list(csv.DictReader(handle))
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        errors, loss, image = (folder/name for name in ('errors.dat','loss.dat','plot.png'))
        with errors.open('w') as file:
            for rate in ('250000','500000'):
                for row in bits:
                    if row['symbol_rate']==rate and row['mode']=='baseline':
                        center = int(row['payload_decile'])*10-5
                        ber = 100*int(row['data_field_bit_errors'])/int(row['data_field_bits_checked'])
                        file.write(f'{center} {ber}\n')
                file.write('\n\n')
        with loss.open('w') as file:
            for rate in ('250000','500000'):
                for row in runs:
                    if row['symbol_rate']==rate and row['mode'] in ('baseline','local_mean_leakage'):
                        pct = 100*(1-int(row['valid_frames'])/int(row['total_frames']))
                        file.write(f'{rate} {pct}\n')
                file.write('\n\n')
        script = f"""
set terminal pngcairo size 1450,660 enhanced font "Arial,16" background rgb "#ffffff"
set output "{image}"
set multiplot layout 1,2 title "Residual QPSK loss on identical IQ recordings" font ",22" margins .088,.963,.17,.84 spacing .12
set border 3 lw 1.2 lc rgb "#4b5563"
set tics nomirror textcolor rgb "#374151"
set grid ytics lc rgb "#e6e9ed"
set title "Where the original receiver made errors"
set xlabel "Position in the frame data field (%)"
set ylabel "Bit errors (%)"
set xrange [0:100]
set xtics 20
set yrange [0:3]
set key top left
plot "{errors}" index 0 using 1:2 with linespoints pt 7 lw 2.4 lc rgb "#1d718e" title "250 ksym/s", \\
     "{errors}" index 1 using 1:2 with linespoints pt 5 lw 2.4 lc rgb "#a25a31" title "500 ksym/s"
set title "Packet loss after leakage tracking"
set xlabel "QPSK symbol rate (ksym/s)"
set ylabel "Packet loss (%)"
set xrange [.5:2.5]
set xtics ("250" 1,"500" 2)
set yrange [-.85:13]
set boxwidth .23 absolute
set style fill solid 1.0 noborder
set key top right
plot "{loss}" index 0 every ::0::0 using (.88):2 with boxes lc rgb "#a25a31" title "Original receiver", \\
     "{loss}" index 1 every ::0::0 using (1.88):2 with boxes lc rgb "#a25a31" notitle, \\
     "{loss}" index 0 every ::1::1 using (1.13):2 with points pt 7 ps 1.4 lc rgb "#1d718e" title "Tracked leakage", \\
     "{loss}" index 1 every ::1::1 using (2.13):2 with points pt 7 ps 1.4 lc rgb "#1d718e" notitle
unset multiplot
"""
        subprocess.run(['gnuplot'], input=script, text=True, check=True)
        target.write_bytes(image.read_bytes())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('target',type=Path)
    args=parser.parse_args()
    plot(args.source,args.target)
