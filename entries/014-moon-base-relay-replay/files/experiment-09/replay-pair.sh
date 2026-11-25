#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
pair_dir="pairs/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$pair_dir"
printf '%s\n' "$pair_dir"
for policy in fifo alerts-first; do
    (
        status=0
        TRACE_POLICY="$policy" HUB_ION_IMAGE=moonbase-dtn-ion:session-gate TCPCL_KEEPALIVE=5 \
            bash run-smoke.sh trace > "$pair_dir/$policy.log" 2>&1 || status=$?
        printf '%s\n' "$status" > "$pair_dir/$policy.exit"
    ) </dev/null &
done
wait
for policy in fifo alerts-first; do
    test "$(cat "$pair_dir/$policy.exit")" = 0
done
