#!/usr/bin/env bash
# Run as root on moonbase-ground. The window owns only the processes it starts.
set -euo pipefail
run=${1:?Pass the experiment directory}
lte=${2:?Pass the srsRAN test directory}
images=${3:?Pass the UHD images directory}
bench=$(cd "$(dirname "$0")" && pwd)
cd "$lte"
test -z "$(pgrep -x srsenb || true)"
test -z "$(pgrep -x srsepc || true)"

# Keep the saved configuration and subscriber database in place.
sed -E 's/^[[:space:]]*tx_gain[[:space:]]*=.*/tx_gain = 65/; s#^filename = logs/enb.log#filename = '"$run"'/enb.log#' \
    configs/enb.conf > "$run/enb.conf"
sed -E 's#^filename = logs/epc.log#filename = '"$run"'/epc.log#' \
    configs/epc.conf > "$run/epc.conf"
chmod 600 "$run/"{enb,epc}.conf
enb=
epc=
capture=
intake=
cleanup() {
    for pid in "$enb" "$capture" "$intake" "$epc"; do
        if [[ -n $pid ]]; then
            kill -INT "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    date -u +%FT%TZ > "$run/rf-stopped"
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
timeout -s INT -k 5s 240s build/srsepc/src/srsepc "$run/epc.conf" > "$run/epc.console" 2>&1 &
epc=$!
for _ in {1..40}; do
    if ip -4 addr show dev moonbase_sgi 2>/dev/null | grep -q '172.16.0.1'; then break; fi
    kill -0 "$epc"
    sleep 0.25
done
ip -4 -brief address show moonbase_sgi
timeout -s INT -k 3s 220s tcpdump -n -l -i moonbase_sgi 'icmp or tcp port 27840' > "$run/sgi.log" 2>&1 &
capture=$!
timeout -s INT -k 3s 220s python3 "$bench/store_forward.py" --db "$run/intake.sqlite3" receive > "$run/intake.jsonl" 2>&1 &
intake=$!
timeout -s INT -k 7s 200s env UHD_IMAGES_DIR="$images" HOME="$lte/fftw-home" \
    LD_PRELOAD="$lte/fftw-home/planning-limit.so" build/srsenb/src/srsenb "$run/enb.conf" > "$run/enb.console" 2>&1 &
enb=$!
while kill -0 "$enb" 2>/dev/null && [[ ! -f $run/stop-rf ]]; do sleep 1; done
