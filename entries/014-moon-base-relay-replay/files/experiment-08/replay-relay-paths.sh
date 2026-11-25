#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
window=${1:-48}
case $window in 16|48) ;; *) printf 'Choose window 16 or 48.\n' >&2; exit 2 ;; esac
out="pairs/relay-path-w$window-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$out"
printf '%s\n' "$out"
for route in stock configured; do
    (
        status=0
        image=moonbase-dtn-hdtn:smoke
        if [[ $route == configured ]]; then image=moonbase-dtn-hdtn:configured-outducts; fi
        TRACE_POLICY=fifo TRACE_DIAGNOSTIC=1 TRACE_WINDOW="$window" HDTN_RELAY_PATH="$route" \
            HDTN_IMAGE="$image" HUB_ION_IMAGE=moonbase-dtn-ion:session-gate TCPCL_KEEPALIVE=5 \
            bash run-smoke.sh trace > "$out/$route.log" 2>&1 || status=$?
        printf '%s\n' "$status" > "$out/$route.exit"
    ) </dev/null &
done
wait
for route in stock configured; do
    test "$(cat "$out/$route.exit")" = 0
done
