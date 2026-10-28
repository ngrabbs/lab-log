#!/usr/bin/env bash
# Optional helper for future repetitions; the first two runs used the commands
# in the entry directly. Run from a computer with SSH/scp access to both Pis.
set -euo pipefail
: "${TX_HOST:?Set TX_HOST to user@transmitter-host}"
: "${RX_HOST:?Set RX_HOST to user@receiver-host}"
run=${1:-03}
amplitude=${2:-0.03}
[[ $run =~ ^[0-9][0-9]$ ]] || exit 2
[[ $amplitude =~ ^0\.[0-9]+$ ]] || exit 2
here=$(cd -- "$(dirname -- "$0")" && pwd)
remote=/home/ngrabbs/work/bpsk-fm-test
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
ssh "$RX_HOST" "mkdir -p $remote; test ! -e $remote/rx$run.iq"
ssh "$TX_HOST" "mkdir -p $remote"
scp "$here/modem.py" "$RX_HOST:$remote/"
scp "$here/transmit.py" "$TX_HOST:$remote/"
ssh "$RX_HOST" "cd $remote && python3 modem.py encode --message 'EMBER > outpost1: BPSK/FM test 2026-10-28' --count 3 --amplitude $amplitude --wav tx$run.wav"
scp "$RX_HOST:$remote/tx$run.wav" "$scratch/tx.wav"
scp "$scratch/tx.wav" "$TX_HOST:$remote/tx$run.wav"
ssh "$RX_HOST" "cd $remote && date -u +%FT%TZ > rx$run-start.txt && rtl_sdr -f 446050000 -s 240000 -g 0.9 -n 5760000 rx$run.iq > rx$run-rtl.log 2>&1" &
capture_pid=$!
ready=false
for attempt in {1..20}; do
    if ssh "$RX_HOST" "grep -q 'Reading samples' $remote/rx$run-rtl.log"; then
        ready=true
        break
    fi
    sleep 0.2
done
if [[ $ready != true ]]; then
    wait "$capture_pid" || true
    echo 'Receiver did not become ready; no transmission started' >&2
    exit 1
fi
sleep 2
ssh "$TX_HOST" "cd $remote && python3 -u transmit.py tx$run.wav > tx$run.log 2>&1 && cat tx$run.log"
wait "$capture_pid"
ssh "$RX_HOST" "cd $remote && python3 modem.py decode rx$run.iq --json rx$run.json"
echo "Captures remain in $remote on the receiver; TX log is on the transmitter."
