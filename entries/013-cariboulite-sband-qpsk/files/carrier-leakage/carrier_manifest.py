"""Record the conducted IQ provenance and write matching SigMF sidecars."""
import argparse
from pathlib import Path
import json
import re


def create(captures, target):
    entries=[]
    for line in (captures/'capture-sha256.txt').read_text().splitlines():
        digest, relpath=line.split()
        file=captures/relpath
        folder=file.parent
        log=(folder/'tx-result.log').read_text()
        rate=int(re.search(r'frequency: ([\d.]+) Hz',log)[1].split('.')[0])
        tune=int(re.search(r'hackrf_set_freq\((\d+)',(folder/'hackrf.log').read_text())[1])
        time=(folder/'capture-start-utc.txt').read_text().strip()
        assert file.stat().st_size==120000000
        desc=(f'{folder.name}. Conducted HiF nominal {rate} Hz, 30 dB pad, TX minimum PA. '
              f'HackRF LNA/VGA 32/24 dB, 2.5 MHz BB, RF amp and bias off. '
              f'Host capture command UTC {time}, sample-zero time uncalibrated.')
        sg={'global':{'core:datatype':'ci8','core:sample_rate':8000000,'core:version':'1.2.0',
                      'core:hw':'HackRF One','core:description':desc},
            'captures':[{'core:sample_start':0,'core:frequency':tune}],
            'annotations':[]}
        (folder/'receive.sigmf-meta').write_text(json.dumps(sg,indent=2)+'\n')
        match=re.search(r'TX_CAL mode=(\w+) I=(\d+) Q=(\d+) startup_I=(\d+) startup_Q=(\d+)',log)
        samples=re.search(r'requested=(\d+) accepted=(\d+) partial=(\d+)',log)
        assert match and samples and samples[1]==samples[2] and samples[3]=='0'
        entries.append({'run':folder.name,'sha256':digest,'bytes':file.stat().st_size,
                        'tx_frequency_hz':rate,'capture_command_start_utc':time,'tx_iq_samples_accepted':int(samples[2]),
                        'auto_calibration_mode':match[1],'rf24_i':int(match[2]),'rf24_q':int(match[3]),
                        'startup_i':int(match[4]),'startup_q':int(match[5]),'sigmf':sg})
    assert len(entries)==13
    target.write_text(json.dumps(entries,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    create(args.captures,args.output)
