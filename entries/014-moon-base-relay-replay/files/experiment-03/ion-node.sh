#!/usr/bin/env bash
set -euo pipefail
node=$1
role=$2
relay_port=$3
agent_options=()
if [[ -n ${TCPCL_KEEPALIVE:-} ]]; then
    agent_options=(--keepalive "$TCPCL_KEEPALIVE")
fi
mkdir -p /run/ion
cd /run/ion

cat > startup.ionrc <<RC
1 $node
s
m horizon +0
a range +0 +3600 10 20 1
a range +0 +3600 20 10 1
a range +0 +3600 20 30 1
a range +0 +3600 30 20 1
a contact +0 +3600 10 20 1000000
a contact +0 +3600 20 10 1000000
a contact +0 +3600 20 30 1000000
a contact +0 +3600 30 20 1000000
RC
cat > startup.bprc <<RC
1
a scheme ipn 'ipnfw' 'ipnadminep'
a endpoint ipn:$node.0 x
a endpoint ipn:$node.1 q
a endpoint ipn:$node.2 q
a protocol tcp4 1400 100
a induct tcp4 ${role}in 'tcp4cli ${role}in'
a outduct tcp4 ${role}in 'tcp4clo ${role}in'
a induct tcp4 ${role}out 'tcp4cli ${role}out'
a outduct tcp4 ${role}out 'tcp4clo ${role}out'
r 'ipnadmin startup.ipnrc'
w 1
s
RC
printf 'a plan 20 tcp4/%sout\n' "$role" > startup.ipnrc
ionadmin startup.ionrc
bpadmin startup.bprc

tcpclv4_agent --duct "${role}in" --node-id "ipn:$node.0" --listen 0.0.0.0:4556 "${agent_options[@]}" > passive.log 2>&1 &
passive_pid=$!
tcpclv4_agent --duct "${role}out" --node-id "ipn:$node.0" --connect "relay:$relay_port" "${agent_options[@]}" > active.log 2>&1 &
active_pid=$!
trap 'kill "$passive_pid" "$active_pid" 2>/dev/null || true' EXIT
trap 'exit 0' TERM INT
wait -n "$passive_pid" "$active_pid"
