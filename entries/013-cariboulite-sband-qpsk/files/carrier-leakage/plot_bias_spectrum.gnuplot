set datafile separator ","
set terminal pngcairo size 1240,650 enhanced font "Arial,16" background rgb "#ffffff"
set title "TX carrier suppression at 2250 MHz" font ",22"
set border 3 lw 1.2 lc rgb "#4b5563"
set tics nomirror textcolor rgb "#374151"
set xlabel "Offset from the transmitter's carrier (kHz)"
set ylabel "FFT-bin power (dBFS)"
set xrange [-270:70]
set yrange [-95:-15]
set xtics ("−250" -250,"−200" -200,"−150" -150,"−100" -100,"−50" -50,"0" 0,"50" 50)
set grid ytics lc rgb "#e6e9ed"
set key top right
set label 1 "Wanted tone" at -198,-16.5 center offset 0,0.1 tc rgb "#4b5563"
set label 2 "Carrier leakage" at -1,-39 right tc rgb "#4b5563"
plot ARG1 every ::1 using ($1/1000):2 with lines lw 1.8 lc rgb "#a25a31" title "Fresh calibration, no bias", \
     ARG1 every ::1 using ($1/1000):3 with lines lw 1.8 lc rgb "#1d718e" title "Fresh calibration, TX IQ bias"
