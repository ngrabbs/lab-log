#!/usr/bin/env python3
"""Compare application admission during cuts with one native in-flight transfer."""

import json
import subprocess
import sys
import time

from outage import Bench, docker


class GatedBench(Bench):
    contact = True
    previous_sessions = 0

    def relay_removals(self):
        command = ["docker", "logs", self.relay]
        print("+", subprocess.list2cmdline(command), flush=True)
        log = subprocess.check_output(command, stderr=subprocess.STDOUT, timeout=5).decode(errors="replace")
        return log.count("Removing Opportunistic link from ingress connection.. finalDestEid (ipn:10.*)")

    def hub_queue(self, *args):
        return self.ion(self.hub, "python3", "/bench/hub-queue.py", *args).decode()

    def agent_count(self, pattern):
        return int(self.ion(self.hub, "bash", "-c",
                            'grep -Fc "$1" /run/ion/active.log || true',
                            "bash", pattern))

    def gate_status(self):
        return json.loads(self.hub_queue("status"))

    def enqueue(self, record_id):
        body = json.dumps({"id": record_id, "class": "status", "mode": "survey"}, sort_keys=True)
        self.payloads[record_id] = (body + "\n").encode()
        (self.output / f"{record_id}.json").write_bytes(self.payloads[record_id])
        self.hub_queue("enqueue", body)
        self.event("hub_queue_commit", id=record_id)

    def close(self):
        self.contact = False
        self.previous_sessions = self.agent_count("TCPCL session established")
        self.previous_relay_removals = self.relay_removals()
        return super().close()

    def ready(self):
        if not self.contact or self.agent_count("TCPCL session established") <= self.previous_sessions:
            return False
        state = self.ion(self.hub, "cat", "/proc/net/tcp").decode().splitlines()[1:]
        return any(line.split()[2].endswith(":11CC") and line.split()[3] == "01" for line in state)

    def wait_ready(self):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.ready():
                self.event("fresh_hub_session", count=self.agent_count("TCPCL session established"))
                return
            time.sleep(0.15)
        raise RuntimeError("No fresh hub TCPCL session after dock reconnect")

    def reopen(self, *args):
        deadline = time.monotonic() + 25
        while self.relay_removals() == self.previous_relay_removals:
            if time.monotonic() >= deadline:
                raise RuntimeError("Relay did not clear the old hub return route")
            time.sleep(0.25)
        self.event("stale_relay_route_removed")
        restored = super().reopen(*args)
        self.contact = True
        self.wait_ready()
        return restored

    def dispatch(self):
        if not self.ready():
            self.event("dispatch_blocked", contact=self.contact)
            return
        job = json.loads(self.hub_queue("claim"))
        self.ion(self.hub, "bpsendfile", "ipn:10.1", "ipn:30.1", job["path"])
        self.event("hub_injected", id=job["id"])

    def confirm(self, record_id):
        self.collect_receipts({record_id})
        receipt = (self.output / f"{record_id}.receipt.json").read_text().strip()
        self.hub_queue("ack", receipt)
        self.event("hub_queue_confirmed", id=record_id)

    def failure_count(self):
        return self.agent_count("no TCPCL session, failing xfer")

    def delay_hub_egress(self):
        pid = docker("inspect", "--format", "{{.State.Pid}}", self.hub).decode().strip()
        command = ["sudo", "-n", "nsenter", "-t", pid, "-n", "tc", "qdisc", "add",
                   "dev", "eth0", "root", "netem", "delay", "2200ms"]
        print("+", subprocess.list2cmdline(command), flush=True)
        subprocess.run(command, check=True, timeout=5)
        self.event("hub_egress_delayed", milliseconds=2200)

    def run(self):
        roles = (self.hub, self.relay, self.earth)
        state_format = "{{.Name}} {{.State.StartedAt}} {{.RestartCount}}"
        started = docker("inspect", "--format", state_format, *roles)
        docker("exec", "-d", "-w", "/run/ion", self.earth, "bprecvfile", "ipn:30.1", "6")
        docker("exec", "-d", "-w", "/run/ion", self.hub, "bprecvfile", "ipn:10.2", "5")
        initial = self.failure_count()
        closed, session = self.close()
        batch = ["gated-001", "gated-002", "gated-003"]
        for record_id in batch:
            self.enqueue(record_id)
            self.dispatch()
        queued = [[key, "queued", 0] for key in batch]
        assert self.gate_status() == queued
        self.event("durable_queue_verified", rows=queued)
        restored = self.reopen(closed, session, 30, set())
        for record_id in batch:
            self.dispatch()
            self.collect_earth(1)
            self.confirm(record_id)
        batch_failures = self.failure_count() - initial
        self.event("gated_drain", first_commit_s=self.commits[batch[0]] - restored,
                   last_commit_s=self.commits[batch[-1]] - restored,
                   last_receipt_s=self.receipts[batch[-1]] - restored,
                   native_failures=batch_failures)
        assert batch_failures == 0

        target = "gated-lost"
        self.enqueue(target)
        self.dispatch()
        first = self.collect_earth(1, suppress_receipt=True)
        assert first["id"] == target and not first["duplicate"] and first["receipt"] is None
        closed, session = self.close()
        time.sleep(5)
        self.hub_queue("retry", target)
        self.event("application_retry_queued", id=target)
        self.dispatch()
        assert self.gate_status()[-1] == [target, "queued", 1]
        restored = self.reopen(closed, session, 10, {f"testfile{i}" for i in range(1, 5)})
        self.dispatch()
        repeat = self.collect_earth(1)
        assert repeat["id"] == target and repeat["duplicate"]
        self.confirm(target)
        lost_failures = self.failure_count() - initial - batch_failures
        self.event("gated_lost_receipt", id=target, final_receipt_s=self.receipts[target] - restored,
                   native_failures=lost_failures, attempts=2)
        assert lost_failures == 0

        target = "gated-inflight"
        self.enqueue(target)
        previous = self.agent_count("TX xfer ")
        self.delay_hub_egress()
        self.dispatch()
        deadline = time.monotonic() + 1.4
        while self.agent_count("TX xfer ") == previous:
            if time.monotonic() >= deadline:
                raise RuntimeError("No native TX observed within fault injection window")
            time.sleep(0.05)
        self.event("native_transfer_in_progress", id=target)
        closed, session = self.close()
        assert self.gate_status()[-1] == [target, "inflight", 1]
        restored = self.reopen(closed, session, 12, {f"testfile{i}" for i in range(1, 6)})
        arrived = self.collect_earth(1)
        assert arrived["id"] == target and not arrived["duplicate"]
        self.confirm(target)
        state = self.gate_status()
        assert state == [[key, "acked", 2 if key == "gated-lost" else 1] for key in self.payloads]
        assert started == docker("inspect", "--format", state_format, *roles)
        self.event("inflight_recovered", id=target, native_failures=self.failure_count() - initial,
                   final_receipt_s=self.receipts[target] - restored, hub_queue=state)
        for container, filename in ((self.earth, "earth.sqlite3"), (self.hub, "hub.sqlite3")):
            docker("cp", f"{container}:/run/ion/{filename}", str(self.output / filename))


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit("Usage: gated.py OUT UPLINK HUB RELAY EARTH")
    GatedBench(*sys.argv[1:]).run()
