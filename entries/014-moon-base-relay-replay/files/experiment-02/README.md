# BPv7 and TCPCLv4 smoke test

Run these commands in this directory on an x86-64 Linux host with Docker
and Python 3. The two Docker builds fetch pinned upstream revisions.
ION uses the opt-in external TCPCLv4 agent. HDTN uses the one-process
relay binary from v3.0.0. Each compile is limited to four jobs.

~~~sh
docker build --progress=plain -f Dockerfile.ion -t moonbase-dtn-ion:smoke .
docker build --progress=plain -f Dockerfile.hdtn -t moonbase-dtn-hdtn:smoke .
bash run-smoke.sh
~~~

The run creates two internal Docker networks and gives each endpoint only
one network. HDTN is the only process on both networks. No listen ports
are published by Docker. BP node IDs are 10 for hub, 20 for relay, and
30 for Earth. Both hop schedules are open for the smoke test.

The hub sends one known record to Earth. The Earth application compares
its ID and SHA-256, commits the bytes to SQLite, then sends an application
receipt back to the hub in a separate BP bundle. Both sends use ION's
file utilities so the test can compare byte-for-byte output.

The script collects the UTC-stamped evidence in runs/, stops its own
containers, and removes its two networks. The evidence includes the
payload at both ends, the receipt, the Earth ledger, ION agent logs,
HDTN output, topology, and image IDs. The tagged build images remain
available for replay. This always-up smoke test exercises transfer and
return receipt. Outage recovery, sustained data rates, RF, and TLS
require separate runs.
