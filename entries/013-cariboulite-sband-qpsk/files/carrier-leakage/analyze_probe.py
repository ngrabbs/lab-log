"""Measure residual carrier and signed 200 kHz tone levels from a conducted probe."""
import argparse
import csv
from pathlib import Path
import re
import numpy as np

FS = 8_000_000
TONE = 200000
SEGMENT = 524288/2_000_000


def iq(raw,start,stop):
    return raw[start:stop].astype(np.float32).view(np.complex64).ravel()


def spectra(raw,start,stop,n):
    samples = iq(raw,start,stop)
    samples = samples[:len(samples)//n*n].reshape(-1,n)
    win = np.hanning(n)
    powers = abs(np.fft.fftshift(np.fft.fft(samples*win,axis=1),axes=1))**2
    return np.fft.fftshift(np.fft.fftfreq(n,1/FS)), powers/(n*np.sum(win**2))


def tone_intervals(raw, rf_offset):
    n=16384
    # Scan the separated tone bands in short blocks. The carrier frequency
    # itself plays no part in locating the waveform segments.
    f, pos_power = None, []
    neg_power = []
    for a in range(0,len(raw)-n+1,128*n):
        b=min(len(raw),a+128*n)
        f,p=spectra(raw,a,b,n)
        pos_power.extend(np.max(p[:,abs(f-(rf_offset+TONE))<65000],axis=1))
        neg_power.extend(np.max(p[:,abs(f-(rf_offset-TONE))<65000],axis=1))

    def loud_interval(level):
        level = np.array(level)
        mask=level > max(np.median(level)*50,np.max(level)*.10)
        idx=np.flatnonzero(np.diff(np.r_[False,mask,False])).reshape(-1,2)
        a,b=max(idx,key=lambda v:v[1]-v[0])
        assert .24 < (b-a)*n/FS < .29
        return (a+.5)*n/FS,(b-.5)*n/FS

    return sorted([(TONE,*loud_interval(pos_power)),(-TONE,*loud_interval(neg_power))],key=lambda p:p[1])


def line(f, p, center, search):
    # The channel's clocks are independent. Find the peak in each spectral
    # block and integrate its five bins, then take the median block power.
    indices=np.flatnonzero(abs(f-center)<search)
    chosen=indices[np.argmax(p[:,indices],axis=1)]
    rows=np.arange(len(chosen))
    local=p[rows[:,None],chosen[:,None]+np.arange(-2,3)]
    a,b,c=10*np.log10(np.maximum(local[:,1:4].T,1e-30))
    shift=np.divide(.5*(a-c),a-2*b+c,out=np.zeros_like(b),where=(a-2*b+c)!=0)
    refined=f[chosen]+np.clip(shift,-.5,.5)*(f[1]-f[0])
    return float(np.median(refined)),float(10*np.log10(np.median(np.sum(local,axis=1))/(127**2)))


def probe(folder, row):
    raw=np.memmap(folder/'receive.sigmf-data',dtype=np.int8,mode='r').reshape(-1,2)
    assert len(raw)==60_000_000
    tx,rx=(int(row[k]) for k in ('tx_hz','rx_hz'))
    expected_center=tx-rx
    first,second=tone_intervals(raw,expected_center)
    sign,start,stop=first
    def region(a,b):
        return spectra(raw,round(a*FS),round(b*FS),65536)
    f,p=region(start+.03,stop-.03)
    tone_1,level_1=line(f,p,expected_center+sign,65000)
    actual_center=tone_1-sign
    _,leak1=line(f,p,actual_center,650)
    f,p=region(second[1]+.03,second[2]-.03)
    tone_2,level_2=line(f,p,actual_center+second[0],1200)
    _,leak2=line(f,p,actual_center,650)
    f,p=region(stop+.035,second[1]-.035)
    leak_freq,leak_zero=line(f,p,actual_center,650)
    f,p=region(.15,.65)
    _,idle_carrier=line(f,p,actual_center,650)
    _,idle_dc=line(f,p,0,650)
    readings=re.search(r'TX_CAL mode=(\S+) I=(\d+) Q=(\d+) startup_I=(\d+) startup_Q=(\d+)',(folder/'tx-result.log').read_text())
    assert readings and readings[1]==row['mode']
    rails=sum(np.count_nonzero((raw[k:k+2_000_000]==127)|(raw[k:k+2_000_000]==-128)) for k in range(0,len(raw),2_000_000))
    return {
        **row,'cal_i':int(readings[2]),'cal_q':int(readings[3]),
        'startup_i':int(readings[4]),'startup_q':int(readings[5]),
        'first_tone_hz':rx+tone_1,'second_tone_hz':rx+tone_2,
        'carrier_rf_hz':rx+leak_freq,'carrier_from_tone_center_hz':rx+actual_center,
        'carrier_rx_offset_hz':leak_freq,
        'first_tone_dbfs':level_1,'second_tone_dbfs':level_2,
        'zero_iq_carrier_dbfs':leak_zero,'zero_iq_carrier_relative_to_first_tone_db':leak_zero-level_1,
        'carrier_during_first_tone_dbfs':leak1,'carrier_during_second_tone_dbfs':leak2,
        'first_tone_carrier_dbc':leak1-level_1,'second_tone_carrier_dbc':leak2-level_2,
        'tx_idle_at_carrier_dbfs':idle_carrier,'rx_dc_tx_idle_dbfs':idle_dc,
        'adc_rail_components':rails,'first_tone_start_s':start,'second_tone_start_s':second[1]
    }


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schedule',type=Path)
    parser.add_argument('captures',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    data=[]
    with args.schedule.open() as handle:
        for row in csv.DictReader(handle,delimiter='\t'):
            measurement=probe(args.captures/row['run'],row)
            data.append(measurement)
            print(row['run'],measurement['cal_i'],measurement['cal_q'],
                  round(measurement['carrier_rf_hz'],1),
                  round(measurement['first_tone_dbfs'],2),round(measurement['zero_iq_carrier_dbfs'],2),
                  round(measurement['first_tone_carrier_dbc'],2),measurement['adc_rail_components'])
    with args.output.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(data[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)
