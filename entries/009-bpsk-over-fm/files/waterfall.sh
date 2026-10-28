#!/usr/bin/env bash
set -euo pipefail
cd /home/ngrabbs/work/bpsk-fm-test
client=satnogs_satnogs-client
usb=/dev/bus/usb/001/003
if sudo -n fuser "$usb" >/dev/null 2>&1; then
  echo 'RTL-SDR is already in use; wait for the observation/receiver to finish.' >&2
  exit 1
fi
if [[ $(sudo -n docker inspect --format '{{.State.Paused}}' "$client") != false ]]; then
  echo 'SatNOGS is already paused; leaving its state untouched.' >&2
  exit 1
fi
cleanup() {
  sudo -n docker stop --time 2 bpsk-waterfall >/dev/null 2>&1 || true
  sudo -n docker unpause "$client" >/dev/null
}
sudo -n docker pause "$client" >/dev/null
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
sudo -n docker run --rm --init -it --name bpsk-waterfall --network none \
  --env "TERM=${TERM:-xterm-256color}" --device "$usb" \
  -v /home/ngrabbs/work/bpsk-fm-test:/work -w /work \
  --entrypoint /usr/bin/python3 librespace/satnogs-client:2.1.2 \
  live_waterfall.py "$@"
