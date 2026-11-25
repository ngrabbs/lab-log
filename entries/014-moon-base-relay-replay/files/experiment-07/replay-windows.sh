#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out="pairs/window-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$out"
printf '%s\n' "$out"
for window in 16 48 128; do
    (
        status=0
        TRACE_POLICY=fifo TRACE_DIAGNOSTIC=1 TRACE_WINDOW="$window" \
            HUB_ION_IMAGE=moonbase-dtn-ion:session-gate TCPCL_KEEPALIVE=5 \
            bash run-smoke.sh trace > "$out/w$window.log" 2>&1 || status=$?
        printf '%s\n' "$status" > "$out/w$window.exit"
    ) </dev/null &
done
wait
for window in 16 48 128; do
    test "$(cat "$out/w$window.exit")" = 0
done
