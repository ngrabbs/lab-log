# CaribouLite conducted S-band QPSK science downlink

Started and updated 2026-11-22. **In progress.**

I wanted to see how much science data the Pi Zero 2 W and CaribouLite could deliver at 2.25 GHz, and how much of it would arrive intact. I sent numbered, synthetic 512-byte science frames at 250 and 500 ksym/s over a conducted link, then decoded the saved HackRF IQ. Each sequence number could earn credit once, after a CRC check and a byte-for-byte comparison.

## Results

Three validation bursts per rate, 256 frames per burst.

| Rate | Valid frames by burst | Total delivered | Packet loss | Packet-train goodput | Whole keyed-burst goodput |
| --- | --- | ---: | ---: | ---: | ---: |
| 250 ksym/s | 116, 108, 110 | 334/768 | 56.5% | 196.0 kbps (190.1–204.2) | 145.7 kbps (141.3–151.8) |
| 500 ksym/s | 176, 180, 177 | 533/768 | 30.6% | 625.6 kbps (619.7–633.8) | 373.2 kbps (369.7–378.1) |

![Observed goodput and packet loss for six conducted 2250 MHz QPSK bursts](images/goodput-and-packet-loss.png)

Each dot is a burst. Squares and labels show the mean. Goodput counts only the 512-byte payloads that passed both checks. The packet-train denominator is the scheduled frame train including all framing overhead. The keyed-burst denominator uses the 10 ms energy gate on the recording, about 3.13 s and 1.95 s respectively. It includes the period of RF energy during startup and around the zero-IQ padding. Without packet loss, this frame format would carry 450.7 or 901.4 kbps within the corresponding packet train.

The [run summaries](files/run-summary.csv) include the receiver gate, clipping check, estimated symbol clock and Pi write counts. The [frame outcomes](files/frames.csv) contain one row per expected sequence per burst, and the [preamble detections](files/detections.csv) retain preamble timings, pilot-fit diagnostics and CRC flags. The [Pi transmit logs](files/transmit-logs.txt) show that all requested I/Q samples were accepted with zero partial writes. The [capture manifest](files/capture-manifest.json) records each raw capture's SHA-256, settings, host command timestamp and SigMF metadata. The signed 8-bit interleaved originals and their individual SigMF metadata sidecars were preserved on the Mac. TX was idle after the run.

## Wiring and radio settings

With TX idle, remove both antennas and disconnect the spectrum analyzer. Attach the fixed **50 Ω, 30 dB S-band-rated pad** to the CaribouLite **HiF** output, then connect the pad through 50 Ω coax to the HackRF One's RF SMA input. The HackRF stays in receive, with antenna-port power and its RF amplifier disabled. Leave **S1G** outside the signal path. This is a point-to-point coax test at nominal **2250.000 MHz**. The pad's model, measured loss at 2250 MHz and cable loss were unrecorded. The [HackRF One hardware documentation](https://hackrf.readthedocs.io/en/stable/hackrf_one.html) specifies −5 dBm maximum input power.

| Setting | Value |
| --- | --- |
| TX | CaribouLite 6G HiF on a Raspberry Pi Zero 2 W, minimum PA code, CLI gain 0 |
| Pi build | [Merged fork at `7a7c11f`](https://github.com/ngrabbs/cariboulite/tree/7a7c11f9218a3c1858121c049a2ae018308d4267), SMI source version `5658A45097B9795A4F8D5E3`, FPGA loaded by boot service |
| TX files | 2 MS/s, interleaved signed 16-bit little-endian IQ, 12,000 RMS envelope counts, 0.2 s of zero IQ at each end plus zero padding to the DMA block boundary |
| RX | HackRF One on a ThinkPad X1 Carbon, firmware 2024.02.1, host tools 2023.01.1 |
| RX settings | Center 2249.500 MHz, 8 MS/s signed 8-bit IQ, 2.5 MHz baseband filter, 32 dB LNA and 24 dB VGA for validation |
| Capture | 60,000,000 complex samples per burst, 7.5 s, receiver running before TX |
| Modulation | Gray QPSK, root-raised-cosine rolloff 0.35, 12-symbol filter span, no FEC or retransmission |
| Nominal null-to-null width | 337.5 kHz at 250 ksym/s and 675 kHz at 500 ksym/s, derived from symbol rate and rolloff |

## Frame and receiver

Each burst has 256 frames. Each frame starts with 64 constant QPSK symbols and a 128-symbol seeded pseudorandom pilot. The 520-byte data portion has a four-byte little-endian sequence number, 512 deterministic pseudorandom payload bytes and a four-byte little-endian CRC-32 over sequence and payload. Each byte goes out most significant bit first, with the first bit in each pair selecting the I sign and the second selecting the Q sign. The burst carries 131,072 potential science bytes. It lasts 2.326528 s at 250 ksym/s and 1.163264 s at 500 ksym/s, excluding padding and RF startup. The [250 ksym/s](files/qpsk-250000.json) and [500 ksym/s](files/qpsk-500000.json) waveform manifests give file sizes, generation parameters and hashes.

The [bench script](files/qpsk_bench.py) regenerates the waveforms and decodes interleaved signed 8-bit receive IQ using NumPy 1.26.4 and SciPy 1.11.4. It translates the 500 kHz receive LO offset, decimates to 2 MS/s, looks for a sustained burst, estimates residual carrier offset and applies an RRC matched filter. It correlates the known pilot in both IQ orientations, fits symbol spacing from the detections and interpolates samples at symbol times. The pilot fits a complex gain, conjugate image term, carrier leakage term and a small residual frequency correction. A smoothed fourth-power QPSK phase estimate tracks phase through the payload. The transmitted science bytes are used after demodulation to verify the CRC-valid payload.

```sh
python3 qpsk_bench.py generate 250000 qpsk-250000.cs16
python3 qpsk_bench.py generate 500000 qpsk-500000.cs16
# On the receiver, start this first. Wait until receive samples are flowing.
hackrf_transfer -r receive.sigmf-data -f 2249500000 -a 0 -p 0 -l 32 -g 24 -b 2500000 -s 8000000 -n 60000000
# On the Pi, play one bounded waveform through HiF.
timeout -k 2 10 cariboulite-tx -c 1 -f 2250000000 -r 2000000 qpsk-250000.cs16
# Substitute the 500000 file and symbol rate for the other test condition.
python3 qpsk_bench.py decode 250000 receive.sigmf-data --out decoded-250
```

## Receiver bring-up

At 16 dB LNA and 16 dB VGA, the 250 ksym/s capture showed energy near the expected frequency but fell below the decoder's sustained-burst gate. At 32/24 dB the 250 ksym/s burst yielded 256 preamble detections and zero valid CRCs with the initial detector. Adding the pilot-based image and carrier-leakage correction recovered 65 frames from the same IQ. Adding fourth-power phase tracking brought that capture to 115/256 and a separate exploratory 500 ksym/s capture to 185/256. Those captures were used to develop the receiver. The validation bursts were taken afterward, alternating the rates with gain and decoder held constant.

## What the run established

The 500 ksym/s condition delivered about 3.19× the packet-train goodput of 250 ksym/s in this setup. It still lost about three out of ten science frames. All six bursts had 256 candidate preambles, no duplicate accepted frames and no samples at the receive ADC rails. The measured carrier offset relative to the two radios' nominal tuning was +21.59 to +21.71 kHz. The pilot fit indicated a residual carrier term around −6 dB relative to the wanted term before equalization, and a conjugate image around −30 dB.

There was substantial repetition by sequence. At 250 ksym/s, 126 sequence numbers failed in all three bursts. At 500 ksym/s, 67 did. The repeated test also reused the same payload and the same position in the burst for each sequence, so this cannot distinguish data-dependent distortion from a timing-dependent impairment. A rerun with shuffled sequence order, independent payload seeds and a calibrated input-level sweep would help separate those possibilities before selecting FEC or estimating a flight data rate.

This measures finite, buffered transmission with offline reception. There is no calibrated S-band TX power, input level, SNR or EVM instrument measurement. Bench pilot EVM is an in-sample statistic after fitting the same pilot and the run summary reports its median only for accepted frames. The experiment did not exercise flight Doppler, antenna losses, free-space path loss, live receiver throughput, long-run Pi underruns or a sustained spacecraft data source. Three bursts per rate sample repeatability on this one bench path. Frames within a burst can share impairments.
