#!/usr/bin/env bash
set -euo pipefail
modem=${1:?Pass the live LilyGO modem index}
run=${2:?Pass the experiment directory}
field() {
    awk -v name="$1" '$1 == name {print $NF}'
}

info=$(mmcli -m "$modem" -K)
grep -q 'SIMCOM_SIM7600G-H' <<< "$info"
device=$(awk '/modem.generic.ports.value.*\(net\)/ {print $(NF-1)}' <<< "$info")
[[ $device =~ ^wwan[0-9]+$ ]]
peer=172.16.0.1
operator=99970

if [[ $(field modem.3gpp.operator-code <<< "$info") != "$operator" ]]; then
    mmcli -m "$modem" --timeout=35 --3gpp-register-in-operator="$operator" || true
fi
for _ in {1..16}; do
    info=$(mmcli -m "$modem" -K)
    if [[ $(field modem.3gpp.operator-code <<< "$info") == "$operator" ]]; then break; fi
    sleep 1
done
[[ $(field modem.3gpp.operator-code <<< "$info") == "$operator" ]]
mmcli -m "$modem" --timeout=25 --simple-connect='apn=srsapn,ip-type=ipv4,allow-roaming=no'

data=
for bearer in $(mmcli -m "$modem" -K | awk '/^modem.generic.bearers.value\[/ {print $NF}'); do
    report=$(mmcli -b "$bearer" -K)
    if [[ $(field bearer.status.connected <<< "$report") == yes &&
          $(field bearer.status.interface <<< "$report") == "$device" ]]; then
        data=$(field bearer.ipv4-config.address <<< "$report")
        break
    fi
done
[[ $data =~ ^172\.16\.0\.([0-9]{1,3})$ ]] && [[ $data != "$peer" ]]
printf '%s %s\n' "$device" "$data" > "$run/bearer-ip.txt"
ip link set "$device" up
ip address add "$data/32" dev "$device"
ip route add "$peer/32" dev "$device" src "$data"
ip -4 route get "$peer"
ping -I "$device" -c 3 -W 2 "$peer"
