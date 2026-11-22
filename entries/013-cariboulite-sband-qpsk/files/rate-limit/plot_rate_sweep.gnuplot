set datafile separator ","
set terminal pngcairo size 1440,630 enhanced font "Arial,16" background rgb "#ffffff"
set multiplot layout 1,2 title "2250 MHz conducted QPSK rate sweep" font ",22" margins .078,.97,.16,.84 spacing .11
set border 3 lw 1.2 lc rgb "#4b5563"
set tics nomirror textcolor rgb "#374151"
set grid ytics lc rgb "#e6e9ed"
set xrange [.45:1.53]
set xtics .5,.25,1.5
set xlabel "QPSK symbol rate (Msym/s)"
set arrow from first 1.48148, graph 0 to first 1.48148, graph 1 nohead dt 2 lw 1.3 lc rgb "#596372" back
set title "Delivered payload with the 2 MS/s profile"
set ylabel "Packet-train goodput (Mbps)"
set yrange [.6:2.85]
set label 1 "2 MS/s waveform ceiling" at 1.465, .74 right tc rgb "#596372" font ",13"
set key top left font ",13"
plot ARG1 using (strcol(1)[1:5] eq "rate-" ? $2/1e6 : 1/0):($12/1e6) with linespoints pt 7 lw 2.1 lc rgb "#1d718e" title "256-frame bursts", \
     ARG1 using (strcol(1)[1:5] eq "long-" ? $2/1e6 : 1/0):($12/1e6) with points pt 6 ps 2.7 lw 1.7 lc rgb "#a25a31" title "10,240-frame run"
unset label 1
set title "Error vector magnitude on held-out pilots"
set ylabel "Median pilot EVM (%)"
set yrange [0:28]
plot ARG1 using (strcol(1)[1:5] eq "rate-" ? $2/1e6 : 1/0):13 with linespoints pt 7 lw 2.1 lc rgb "#a25a31" title "Carrier tracking", \
     ARG1 using (strcol(1)[1:5] eq "rate-" ? $2/1e6 : 1/0):16 with linespoints pt 5 lw 2.1 lc rgb "#1d718e" title "Pilot equalizer"
unset multiplot
