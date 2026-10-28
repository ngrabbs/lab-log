#!/usr/bin/env python3
"""Live terminal waterfall for the existing SatNOGS RTL-SDR container."""
import argparse
import collections
import curses
import subprocess
import time
import numpy as np

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--seconds',type=float,default=0,help='Stop automatically after N seconds; 0 runs until q/Ctrl-C')
a=p.parse_args()
fs=240000
nfft=8192
center=446050000
target=446000000
span=40000
window=np.hanning(nfft)
freq=np.fft.fftshift(np.fft.fftfreq(nfft,1/fs))+center
select=np.flatnonzero(abs(freq-target)<=span/2)

def display(screen):
    curses.curs_set(0)
    screen.nodelay(True)
    colorful=curses.has_colors()
    if colorful:
        curses.start_color()
        colors=[17,18,19,20,21,27,33,39,45,51,50,49,48,47,46,82,118,154,190,226,220,214,208,202,196,203,210,217,224,231]
        for i,c in enumerate(colors,1):
            curses.init_pair(i,c if curses.COLORS>=256 else min(7,i//4),curses.COLOR_BLACK)
    else:
        colors=[0]*30
    rows=collections.deque(maxlen=300)
    proc=subprocess.Popen(['rtl_sdr','-f',str(center),'-s',str(fs),'-g','0.9','-'],
                          stdout=subprocess.PIPE,stderr=open('/work/waterfall-rtl.log','w'))
    start=time.monotonic()
    try:
        while not a.seconds or time.monotonic()-start<a.seconds:
            key=screen.getch()
            if key in (ord('q'),ord('Q'),3):break
            data=proc.stdout.read(nfft*2*4)
            if len(data)!=nfft*2*4:
                raise RuntimeError('RTL-SDR stream ended; see waterfall-rtl.log')
            raw=np.frombuffer(data,dtype=np.uint8).reshape(4,nfft,2).astype(float)
            iq=(raw[:,:,0]-127.5+1j*(raw[:,:,1]-127.5))/127.5
            power=np.mean(abs(np.fft.fftshift(np.fft.fft(iq*window,axis=1),axes=1)/window.sum())**2,axis=0)
            height,width=screen.getmaxyx()
            width=max(1,width-1)
            groups=np.array_split(power[select],width)
            db=10*np.log10(np.array([g.mean() if len(g) else 1e-20 for g in groups])+1e-20)
            levels=np.clip(((db+95)/55*(len(colors)-1)).astype(int),0,len(colors)-1)
            rows.appendleft(levels)
            screen.erase()
            title='446 MHz LIVE | RTL-SDR Blog V4 | gain 0.9 dB | q / Ctrl-C quits'
            screen.addnstr(0,0,title,width,curses.A_BOLD)
            screen.addnstr(1,0,'445.980 MHz'+' ' * max(1,(width-31)//2)+'446.000'+' ' * max(1,(width-31)//2)+'446.020',width)
            screen.addnstr(2,0,'Newest at top | FFT bin dBFS, uncalibrated | color scale -95 to -40',width)
            for y,line in enumerate(list(rows)[:max(0,height-4)],3):
                for x,level in enumerate(line[:width]):
                    char=' .:-=+*#%@'[min(9,int(level)*10//len(colors))]
                    try:screen.addch(y,x,char,curses.color_pair(int(level)+1) if colorful else 0)
                    except curses.error:pass
            screen.refresh()
    finally:
        proc.terminate()
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill();proc.wait()

try:curses.wrapper(display)
except KeyboardInterrupt:pass
