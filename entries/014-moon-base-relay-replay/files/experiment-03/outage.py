#!/usr/bin/env python3
"""Run two contact-loss trials after the Experiment 2 nodes are ready."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time


def docker(*args):
    command = ("docker", *args)
    print("+", subprocess.list2cmdline(command), flush=True)
    completed = subprocess.run(command, capture_output=True, timeout=20)
    if completed.returncode:
        raise RuntimeError(completed.stderr.decode(errors="replace").strip())
    return completed.stdout


class Bench:
    def __init__(self, output, network, hub, relay, earth):
        self.output = Path(output)
        self.network = network
        self.hub, self.relay, self.earth = hub, relay, earth
        self.payloads = {}
        self.commits = {}
        self.receipts = {}
        self.positions = {hub: 1, earth: 1}
        self.timeline = self.output / "timeline.jsonl"

    def event(self, name, **fields):
        now = time.monotonic()
        entry = {"event": name, "utc": datetime.now(timezone.utc).isoformat(),
                 "monotonic_s": now, **fields}
        with self.timeline.open("a") as stream:
            stream.write(json.dumps(entry) + "\n")
        print(json.dumps(entry), flush=True)
        return now

    def ion(self, node, *args):
        return docker("exec", "-w", "/run/ion", node, *args)

    def send(self, record_id):
        if record_id not in self.payloads:
            body = (json.dumps({"id": record_id, "class": "status", "mode": "survey"},
                               sort_keys=True) + "\n").encode()
            self.payloads[record_id] = body
            path = self.output / f"{record_id}.json"
            path.write_bytes(body)
            docker("cp", str(path), f"{self.hub}:/run/ion/{path.name}")
        self.ion(self.hub, "bpsendfile", "ipn:10.1", "ipn:30.1", f"/run/ion/{record_id}.json")
        self.event("hub_injected", id=record_id)

    def files(self, node):
        return set(self.ion(node, "bash", "-c", 'shopt -s nullglob; printf "%s\\n" testfile[0-9]*').decode().split())

    def earth_session(self):
        table = self.ion(self.earth, "cat", "/proc/net/tcp").decode().splitlines()[1:]
        rows = [line.split() for line in table]
        return {row[9] for row in rows if row[2].endswith(":11CD") and row[3] == "01"}

    def close(self):
        session = self.earth_session()
        assert session, "Earth-to-relay TCP session is missing"
        docker("network", "disconnect", self.network, self.hub)
        closed = self.event("uplink_closed", earth_session=sorted(session))
        networks = json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Networks}}", self.hub))
        assert not networks, f"Hub attached to unexpected networks: {networks}"
        return closed, session

    def reopen(self, closed, session, duration, expected_earth_files):
        time.sleep(max(0, closed + duration - time.monotonic()))
        assert self.files(self.earth) == expected_earth_files, "Unexpected Earth arrival while cut"
        assert self.earth_session() == session, "Earth-to-relay TCP session changed during cut"
        self.event("outage_verified", earth_files=len(expected_earth_files),
                   earth_session=sorted(session))
        docker("network", "connect", "--alias", "hub", self.network, self.hub)
        return self.event("uplink_restored", closed_seconds=time.monotonic() - closed)

    def receive(self, node, deadline):
        number = self.positions[node]
        filename = f"testfile{number}"
        while time.monotonic() < deadline:
            output = subprocess.run(
                ["docker", "exec", "-w", "/run/ion", node, "bash", "-c",
                 'test -s "$1" && cat "$1"', "bash", filename],
                capture_output=True, check=False, timeout=5,
            )
            if output.returncode == 0 and output.stdout.endswith(b"\n"):
                self.positions[node] += 1
                return filename, output.stdout
            time.sleep(0.15)
        raise RuntimeError(f"Timed out waiting for {node} {filename}")

    def collect_earth(self, count, suppress_receipt=False):
        deadline = time.monotonic() + 30
        for _ in range(count):
            filename, body = self.receive(self.earth, deadline)
            record_id = json.loads(body)["id"]
            assert body == self.payloads[record_id], "Earth payload does not match input"
            digest = hashlib.sha256(body).hexdigest()
            flags = ["--suppress-receipt"] if suppress_receipt else []
            shaped = json.loads(self.ion(self.earth, "python3", "/bench/ledger.py",
                                         filename, digest, *flags))
            event = "earth_duplicate" if shaped["duplicate"] else "earth_commit"
            now = self.event(event, id=record_id, sha256=digest,
                             receipt_suppressed=suppress_receipt)
            if not shaped["duplicate"]:
                self.commits[record_id] = now
            if shaped["receipt"]:
                self.ion(self.earth, "bpsendfile", "ipn:30.2", "ipn:10.2", shaped["receipt"])
        return shaped

    def collect_receipts(self, expected):
        deadline = time.monotonic() + 30
        for _ in expected:
            _, body = self.receive(self.hub, deadline)
            record_id = json.loads(body)["id"]
            digest = hashlib.sha256(self.payloads[record_id]).hexdigest()
            assert json.loads(body) == {"id": record_id, "sha256": digest, "disposition": "committed"}
            assert record_id not in self.receipts, f"Repeated receipt for {record_id}"
            (self.output / f"{record_id}.receipt.json").write_bytes(body)
            self.receipts[record_id] = self.event("hub_receipt", id=record_id, sha256=digest)
        assert expected <= self.receipts.keys()

    def run(self):
        roles = (self.hub, self.relay, self.earth)
        state_format = "{{.Name}} {{.State.StartedAt}} {{.RestartCount}}"
        started = docker("inspect", "--format", state_format, *roles)
        docker("exec", "-d", "-w", "/run/ion", self.earth, "bprecvfile", "ipn:30.1", "5")
        docker("exec", "-d", "-w", "/run/ion", self.hub, "bprecvfile", "ipn:10.2", "4")
        records = {"outage-001", "outage-002", "outage-003"}
        closed, session = self.close()
        for record_id in sorted(records):
            self.send(record_id)
        restored = self.reopen(closed, session, 30, set())
        self.collect_earth(3)
        self.collect_receipts(records)
        self.event("drain", first_commit_s=min(self.commits[key] for key in records) - restored,
                   last_commit_s=max(self.commits[key] for key in records) - restored,
                   last_receipt_s=max(self.receipts[key] for key in records) - restored)

        target = "lost-001"
        self.send(target)
        first = self.collect_earth(1, suppress_receipt=True)
        assert first["id"] == target and not first["duplicate"] and first["receipt"] is None
        assert self.files(self.hub) == {"testfile1", "testfile2", "testfile3"}
        closed, session = self.close()
        # Application timeout is explicit for this fixture. Process lifetimes stay unchanged.
        time.sleep(5)
        self.event("application_receipt_timeout", id=target)
        self.send(target)
        restored = self.reopen(closed, session, 10, {f"testfile{i}" for i in range(1, 5)})
        repeat = self.collect_earth(1)
        assert repeat["id"] == target and repeat["duplicate"]
        self.collect_receipts({target})
        database = self.output / "earth.sqlite3"
        docker("cp", f"{self.earth}:/run/ion/earth.sqlite3", str(database))
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as db:
            stored = dict(db.execute("SELECT id, payload FROM records"))
        assert stored == self.payloads, "Unexpected records in the Earth ledger"
        assert started == docker("inspect", "--format", state_format, *roles), "Container restarted"
        self.event("lost_receipt_verified", id=target, observed_arrivals=2, durable_rows=1,
                   final_receipt_s=self.receipts[target] - restored, container_restarts=0)


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit("Usage: outage.py OUT UPLINK HUB RELAY EARTH")
    Bench(*sys.argv[1:]).run()
