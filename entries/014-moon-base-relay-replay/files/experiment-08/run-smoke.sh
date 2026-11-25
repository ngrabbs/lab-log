#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
root=$PWD
mode=${1:-smoke}
ion_env=()
if [[ $mode != smoke && $mode != outage && $mode != gated && $mode != trace ]]; then
    printf 'Usage: bash run-smoke.sh [smoke|outage|gated|trace]\n' >&2
    exit 2
fi
if [[ $mode != smoke ]]; then
    ion_env=(-e TCPCL_KEEPALIVE="${TCPCL_KEEPALIVE:-3}")
fi
run_id=$(date -u +%Y%m%dT%H%M%SZ)
if [[ $mode == trace ]]; then
    : "${TRACE_POLICY:?Set TRACE_POLICY to fifo or alerts-first}"
    case $TRACE_POLICY in fifo|alerts-first) ;; *) exit 2 ;; esac
    run_id=$run_id-$TRACE_POLICY
    if [[ ${TRACE_DIAGNOSTIC:-0} == 1 ]]; then
        run_id=$run_id-w${TRACE_WINDOW:?Set diagnostic window}
        if [[ -n ${HDTN_RELAY_PATH:-} ]]; then
            case $HDTN_RELAY_PATH in stock|configured) ;; *) exit 2 ;; esac
            run_id=$run_id-$HDTN_RELAY_PATH
        fi
    fi
fi
out="$root/runs/$run_id"
mkdir -p "$(dirname "$out")"
mkdir "$out"
prefix=mb-dtn-$run_id
hub=$prefix-hub
relay=$prefix-relay
earth=$prefix-earth
uplink=$prefix-up
downlink=$prefix-down
ion_image=moonbase-dtn-ion:smoke
hub_ion_image=${HUB_ION_IMAGE:-$ion_image}
hub_mount=()
earth_mount=()
if [[ $mode == trace ]]; then
    mkdir "$out/hub" "$out/earth"
    hub_mount=(--mount "type=bind,src=$out/hub,dst=/run/ion")
    earth_mount=(--mount "type=bind,src=$out/earth,dst=/run/ion")
fi
hdtn_image=${HDTN_IMAGE:-moonbase-dtn-hdtn:smoke}
start=$(date -u +%FT%TZ)

# Retain evidence even if a startup check or a delivery times out.
cleanup() {
    result=$?
    set +e
    set +x
    for role in hub earth; do
        container=$prefix-$role
        for log in ion.log active.log passive.log; do
            docker cp "$container:/run/ion/$log" "$out/$role-$log" >/dev/null 2>&1
        done
        docker logs "$container" > "$out/$role-container.log" 2>&1
    done
    docker stop --time 4 "$relay" >/dev/null 2>&1
    docker logs "$relay" > "$out/relay-container.log" 2>&1
    docker rm -f "$hub" "$relay" "$earth" >/dev/null 2>&1
    docker network rm "$uplink" "$downlink" >/dev/null 2>&1
    printf 'Run %s (%s), exit %s. Evidence: %s\n' "$run_id" "$start" "$result" "$out"
    exit "$result"
}
trap cleanup EXIT
set -x
docker network create --internal --label experiment=moonbase-dtn-smoke "$uplink"
docker network create --internal --label experiment=moonbase-dtn-smoke "$downlink"
docker create --init --label experiment=moonbase-dtn-smoke --name "$relay" --network "$uplink" \
    --network-alias relay --mount "type=bind,src=$root,dst=/bench,readonly" \
    "$hdtn_image" bash /bench/relay-node.sh
docker network connect --alias relay "$downlink" "$relay"
docker run -d --init "${ion_env[@]}" --label experiment=moonbase-dtn-smoke --name "$hub" --network "$uplink" \
    --network-alias hub --mount "type=bind,src=$root,dst=/bench,readonly" \
    "${hub_mount[@]}" \
    "$hub_ion_image" bash /bench/ion-node.sh 10 hub 4556
docker run -d --init "${ion_env[@]}" --label experiment=moonbase-dtn-smoke --name "$earth" --network "$downlink" \
    --network-alias earth --mount "type=bind,src=$root,dst=/bench,readonly" \
    "${earth_mount[@]}" \
    "$ion_image" bash /bench/ion-node.sh 30 earth 4557
docker start "$relay"
docker inspect --format '{{.Name}} networks={{range $name, $net := .NetworkSettings.Networks}}{{$name}} {{end}} published={{json .HostConfig.PortBindings}}' \
    "$hub" "$relay" "$earth" | tee "$out/topology.txt"
docker network inspect --format '{{.Name}} internal={{.Internal}}' "$uplink" "$downlink" | tee -a "$out/topology.txt"
docker image inspect --format '{{index .RepoTags 0}} {{.Id}}' "$hub_ion_image" "$ion_image" "$hdtn_image" > "$out/images.txt"

# Wait for peers to start instead of using a fixed delay.
for role in "$hub" "$earth"; do
    timeout 40s bash -c '
        until docker exec "$1" grep -qi "session established" /run/ion/active.log 2>/dev/null &&
              docker exec "$1" grep -qi "session established" /run/ion/passive.log 2>/dev/null; do
            sleep 1
        done
    ' bash "$role"
done

if [[ $mode != smoke ]]; then
    python3 "$root/$mode.py" "$out" "$uplink" "$hub" "$relay" "$earth"
    exit
fi

printf '%s\n' '{"id":"smoke-001","class":"status","battery_mv":12180,"mode":"survey"}' > "$out/sent.json"
digest=$(sha256sum "$out/sent.json" | cut -d' ' -f1)
docker cp "$out/sent.json" "$hub:/run/ion/payload.json"
docker exec -d -w /run/ion "$earth" bprecvfile ipn:30.1 1
docker exec -d -w /run/ion "$hub" bprecvfile ipn:10.2 1
docker exec -w /run/ion "$hub" bpsendfile ipn:10.1 ipn:30.1 /run/ion/payload.json

wait_for_file() {
    timeout 30s bash -c 'until docker exec "$1" test -s /run/ion/testfile1; do sleep 0.2; done' bash "$1"
}
wait_for_file "$earth"
docker exec -w /run/ion "$earth" python3 /bench/receipt.py smoke-001 "$digest"
docker cp "$earth:/run/ion/testfile1" "$out/earth-received.json"
docker cp "$earth:/run/ion/earth.sqlite3" "$out/earth.sqlite3"
cmp "$out/sent.json" "$out/earth-received.json"
docker exec -w /run/ion "$earth" bpsendfile ipn:30.2 ipn:10.2 /run/ion/receipt.json
wait_for_file "$hub"
docker cp "$hub:/run/ion/testfile1" "$out/hub-receipt.json"
python3 - "$out/hub-receipt.json" "$digest" <<'PY'
import json
from pathlib import Path
import sys

receipt = json.loads(Path(sys.argv[1]).read_text())
expected = {"id": "smoke-001", "sha256": sys.argv[2], "disposition": "committed"}
if receipt != expected:
    raise SystemExit(f"Unexpected receipt: {receipt}")
print(f"Hub received application receipt for {receipt['id']}, SHA-256 {receipt['sha256']}")
PY
