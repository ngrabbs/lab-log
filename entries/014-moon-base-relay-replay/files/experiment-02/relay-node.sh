#!/usr/bin/env bash
set -euo pipefail
mkdir -p /run/hdtn
cd /run/hdtn
python3 - <<'PY'
import json
from pathlib import Path

source = Path("/src/hdtn/config_files/hdtn/hdtn_ingress1tcpclv4_port4556_egress1tcpclv4_port4558flowid2.json")
config = json.loads(source.read_text())
config.update(myNodeId=20, userInterfaceOn=False)
ingress = config["inductsConfig"]["inductVector"]
ingress.append(dict(ingress[0], name="tcpcl_from_earth", boundPort=4557))
egress = config["outductsConfig"]["outductVector"]
egress[0].update(name="tcpcl_to_earth", nextHopNodeId=30, remoteHostname="earth", remotePort=4556,
                 tcpclAllowOpportunisticReceiveBundles=False)
egress.append(dict(egress[0], name="tcpcl_to_hub", nextHopNodeId=10, remoteHostname="hub"))
storage = config["storageConfig"]
storage.update(totalStorageCapacityBytes=64 * 1024 * 1024, storageDiskConfigVector=[
    {"name": "relay", "storeFilePath": "/run/hdtn/relay.bin"}])
Path("relay.json").write_text(json.dumps(config))
edges = ((10, 20), (20, 30), (30, 20), (20, 10))
contacts = [dict(contact=i + 1, source=source, dest=dest, startTime=0,
                 endTime=3600, rateBitsPerSec=0, owlt=1)
            for i, (source, dest) in enumerate(edges)]
Path("contacts.json").write_text(json.dumps({"contacts": contacts}))
PY
exec /src/hdtn/build/module/hdtn_one_process/hdtn-one-process \
    --hdtn-config-file=/run/hdtn/relay.json --contact-plan-file=/run/hdtn/contacts.json
