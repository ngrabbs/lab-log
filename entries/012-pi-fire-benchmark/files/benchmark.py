"""Replay stored triplets serially on a Pi using both projects' pinned runtimes."""
import csv
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter_ns
from unittest.mock import patch

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent
METHODS = ('egse_orb', 'egse_phase_fallback', 'jacob_p', 'jacob_i_registered',
           'jacob_i_independent', 'jacob_whole_frame')
cv2.setNumThreads(1)
cv2.ocl.setUseOpenCL(False)


def elapsed(start):
    return (perf_counter_ns() - start) / 1e6


def read_json(path):
    return json.loads(path.read_text())


def worker():
    from research.anchor_g2.exploratory_jpeg import evaluate_jpeg
    from research.anchor_g2 import provisional

    def evaluate(dataset, capture, mode):
        request = ROOT / 'requests' / f'{dataset}--{capture}--{mode}.json'
        core = {}

        def timed(name, func):
            def call(*args, **kwargs):
                start = perf_counter_ns()
                result = func(*args, **kwargs)
                core[name] = elapsed(start)
                return result
            return call

        with patch.object(provisional, 'primary_p', timed('p', provisional.primary_p)), \
             patch.object(provisional, 'integrated_arithmetic', timed('i', provisional.integrated_arithmetic)):
            start = perf_counter_ns()
            report = evaluate_jpeg(request, opt_in=True)
            total_ms = elapsed(start)
        assert len(report['channel_statistics']) == 3, report['reason_codes']
        data = report.get('provisional', {})
        return dict(mode=mode, total_ms=total_ms, core_ms=core, runtime=report['runtime'],
                    stage_ms={key: value * 1000 for key, value in report['timing_seconds'].items()},
                    state=report['registration']['state'], geometry=report['geometry'],
                    reason=report['registration'].get('reason') or '|'.join(report['reason_codes']),
                    channels=[{k: c[k] for k in ('wavelength_nm', 'sha256', 'shape')}
                              for c in report['channel_statistics']],
                    p={k: data['P_numerical'].get(k) for k in ('numeric_valid', 'reason', 'median_delta',
                         'p99_delta', 'mean_delta', 'valid_fraction_frame')} if data.get('P_numerical') else None,
                    i={k: data['I_numerical'].get(k) for k in ('numeric_ratio', 'additive_excess',
                         'net_continuum', 'reason')} if data.get('I_numerical') else None,
                    net=data.get('net'), gross=data.get('gross') if mode == 'whole-frame' else None,
                    diagnostic_reasons=data.get('reason_codes', []))

    print('ready', flush=True)
    for line in sys.stdin:
        dataset, capture, mode = json.loads(line)
        print(json.dumps(evaluate(dataset, capture, mode), allow_nan=False), flush=True)


def hardware():
    def command(*args):
        return subprocess.check_output(args, text=True).strip()
    cpu = Path('/sys/devices/system/cpu/cpu2/cpufreq')
    return dict(model=Path('/proc/device-tree/model').read_text().strip('\x00'),
                machine=platform.machine(), kernel=platform.release(), affinity=sorted(os.sched_getaffinity(0)),
                governor=(cpu / 'scaling_governor').read_text().strip(),
                temp=command('vcgencmd', 'measure_temp'), throttle=command('vcgencmd', 'get_throttled'),
                load=list(os.getloadavg()))


def phase_fits(report, inputs):
    channels = {c['wavelength_nm']: c for c in inputs.values()}
    shapes = {c['wavelength_nm']: c['shape'] for c in report['channels']}
    assert channels[770]['rotation'] == 0
    for wave, matrix, pair in zip((750, 780), report['geometry']['transforms'][1:], report['geometry']['pairs']):
        matrix = np.array(matrix)
        if channels[wave]['rotation'] == 180:
            height, width = shapes[wave]
            matrix = matrix @ np.array([[-1, 0, width - 1], [0, -1, height - 1], [0, 0, 1]])
        yield matrix, dict(mode='jacob_phase_translation', source_to_reference=matrix.tolist(),
                           ncc=pair['ncc'], wavelength_nm=wave)


def main():
    egse_module, jacob_python, calibration, test2_images, controls = map(Path, sys.argv[1:6])
    sys.path.insert(0, str(egse_module))
    from ember_detector import pipeline

    config = pipeline.load_config(ROOT / 'profile.json')
    baseline_records = read_json(ROOT / 'baseline.json')
    assert len(baseline_records) == 107
    assert pipeline.digest(calibration.read_bytes()) == config['calibration_sha256']
    roots = {'test2': test2_images, 'controls': controls}
    run_start = hardware()

    def jacob(dataset, capture, mode, inputs):
        start = perf_counter_ns()
        print(json.dumps([dataset, capture, mode]), file=child.stdin, flush=True)
        report = json.loads(child.stdout.readline())
        assert {c['wavelength_nm']: c['sha256'] for c in report['channels']} == {
            c['wavelength_nm']: c['sha256'] for c in inputs.values()
        }
        report['worker_roundtrip_ms'] = elapsed(start)
        return report

    def run_case(old):
        dataset, capture = old['dataset'], old['capture']
        def egse():
            return pipeline.run(ROOT / f'{dataset}-manifest.json', capture, config, calibration,
                                live_image_root=roots[dataset])[0]
        start = perf_counter_ns()
        primary = egse()
        primary_ms = elapsed(start)
        assert primary['code_sha256'] == old['code_sha256'] and primary['inputs'] == old['inputs']
        assert (primary['result'], primary['reason']) == (old['result'], old['reason'])
        final, phase = primary, None
        if primary['reason'].startswith(('REGISTRATION_', 'INSUFFICIENT_OVERLAP')):
            phase = jacob(dataset, capture, 'phase', primary['inputs'])
            if phase['state'] == 'ACCEPTED_ENGINEERING_ONLY':
                fits = iter(phase_fits(phase, primary['inputs']))
                with patch.object(pipeline, 'align', side_effect=lambda *_: next(fits)) as align:
                    final = egse()
                assert align.call_count == 2
            hybrid_ms = elapsed(start)
        else:
            hybrid_ms = primary_ms

        registered = jacob(dataset, capture, 'registered-boxes', primary['inputs'])
        independent = jacob(dataset, capture, 'independent-boxes', primary['inputs'])
        whole = jacob(dataset, capture, 'whole-frame', primary['inputs'])
        return dict(dataset=dataset, capture=capture, primary=primary, primary_ms=primary_ms,
                    hybrid=final, hybrid_ms=hybrid_ms, phase=phase, registered=registered,
                    independent=independent, whole=whole)

    with subprocess.Popen([str(jacob_python), '-B', __file__, 'worker'], cwd=ROOT, text=True,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
        assert child.stdout.readline().strip() == 'ready'
        # Warm both runtimes on one known ORB miss before collecting samples.
        warmup = next(r for r in baseline_records if r['dataset'] == 'test2' and r['result'] == 'UNKNOWN')
        run_case(warmup)
        with (ROOT / 'benchmark-records.jsonl').open('x') as stream:
            for i, record in enumerate(baseline_records, 1):
                row = run_case(record)
                print(json.dumps(row, allow_nan=False), file=stream, flush=True)
                if i % 10 == 0 or i == len(baseline_records):
                    print(f'{i}/{len(baseline_records)} triplets benchmarked', flush=True)
        child.stdin.close()
        assert child.wait(timeout=20) == 0
    (ROOT / 'hardware.json').write_text(json.dumps(dict(start=run_start, end=hardware()), indent=2) + '\n')


if __name__ == '__main__':
    worker() if sys.argv[1] == 'worker' else main()
