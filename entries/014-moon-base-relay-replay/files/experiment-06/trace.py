#!/usr/bin/env python3
"""Run a wall-clock telemetry trace through three real BP stacks."""
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from gated import GatedBench
from outage import Bench, docker

RATE = 10 * 1024
WINDOW = 48
HUB_DELAY = 50
EARTH_DELAY = 1250


@dataclass(frozen=True)
class Record:
    key: str
    kind: str
    due: float
    body: bytes
    digest: str


def read_trace(path, limit, rehearsal):
    with gzip.open(path, "rb") as stream:
        trace = stream.read()
    rows = []
    rehearsal_alerts = {
        "alert-outage": 12.0, "alert-contact-open": 28.05, "alert-pass-close": 40.0
    }
    for line in trace.splitlines():
        obj = json.loads(line)
        body = obj["payload"].encode()
        fields = json.loads(body)
        digest = hashlib.sha256(body).hexdigest()
        if digest != obj["sha256"]:
            raise ValueError(f"Trace digest mismatch for {fields['id']}")
        due = fields["t_ms"] / 1000
        if rehearsal and fields["class"] == "alert":
            due = rehearsal_alerts[fields["id"]]
        if due < limit:
            rows.append(Record(fields["id"], fields["class"], due, body, digest))
    return sorted(rows, key=lambda r: (r.due, r.key)), hashlib.sha256(trace).hexdigest()


def sender(node, source, destination, logfile):
    return subprocess.Popen(
        ["docker", "exec", "-i", "-w", "/run/ion", node, "bash", "-c",
         'while IFS= read -r path; do bpsendfile "$1" "$2" "$path" || exit; done',
         "bash", source, destination],
        stdin=subprocess.PIPE, stdout=logfile, stderr=subprocess.STDOUT, text=True,
    )


def submit(worker, filename):
    if worker.poll() is not None:
        raise RuntimeError("ION file sender exited")
    worker.stdin.write(f"/run/ion/{filename}\n")
    worker.stdin.flush()


class Replay(GatedBench):
    def __init__(self, *args):
        super().__init__(*args)
        self.policy = os.environ["TRACE_POLICY"]
        self.rehearsal = os.getenv("TRACE_REHEARSAL") == "1"
        self.rise, self.acquired, self.cutoff = (25, 28, 44) if self.rehearsal else (1800, 1830, 2100)
        self.records, self.trace_digest = read_trace(Path("/").joinpath(
            Path(__file__).resolve().parent, "telemetry.jsonl.gz"), self.cutoff, self.rehearsal)
        self.by_id = {record.key: record for record in self.records}
        self.status_streak = 0
        self.next_send = 0.0
        self.arrivals = Counter()
        self.earth_pos = self.hub_pos = 1
        self.receipt_time = {}
        self.commit_time = {}
        self.first_session = None

    def delay_link(self, node, network=None, milliseconds=50):
        networks = json.loads(docker("inspect", "--format", "{{json .NetworkSettings.Networks}}", node))
        endpoint = networks[network] if network else next(iter(networks.values()))
        pid = docker("inspect", "--format", "{{.State.Pid}}", node).decode().strip()
        prefix = ["sudo", "-n", "nsenter", "-t", pid, "-n"]
        data = json.loads(subprocess.check_output([*prefix, "ip", "-j", "addr"], timeout=5))
        interface = next(row["ifname"] for row in data if any(
            addr["local"] == endpoint["IPAddress"] for addr in row["addr_info"]
        ))
        cmd = [*prefix, "tc", "qdisc", "replace", "dev", interface, "root",
               "netem", "delay", f"{milliseconds}ms"]
        print("+", subprocess.list2cmdline(cmd), flush=True)
        subprocess.run(cmd, check=True, timeout=5)
        self.event("link_delay", role=node.rsplit("-", 1)[-1], interface=interface,
                   milliseconds=milliseconds)

    def read_file(self, role, position):
        path = self.output / role / f"testfile{position}"
        try:
            body = path.read_bytes()
            return body, json.loads(body)
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def poll_earth(self):
        while item := self.read_file("earth", self.earth_pos):
            body, fields = item
            record = self.by_id[fields["id"]]
            if body != record.body:
                raise RuntimeError(f"Earth received unexpected payload for {record.key}")
            with self.earth_db:
                inserted = self.earth_db.execute(
                    "INSERT OR IGNORE INTO records VALUES (?,?,?)",
                    (record.key, record.digest, body),
                ).rowcount
            now = time.monotonic() - self.start
            self.arrivals[record.key] += 1
            if inserted:
                self.commit_time[record.key] = now
            self.log_record("earth_commit" if inserted else "earth_duplicate", record, now)
            filename = f"receipt-{self.earth_pos}.json"
            (self.output / "earth" / filename).write_text(json.dumps(
                {"id": record.key, "sha256": record.digest, "disposition": "committed"}))
            submit(self.earth_sender, filename)
            self.earth_pos += 1

    def poll_hub(self):
        while item := self.read_file("hub", self.hub_pos):
            _, receipt = item
            record = self.by_id[receipt["id"]]
            if receipt != {"id": record.key, "sha256": record.digest, "disposition": "committed"}:
                raise RuntimeError(f"Bad receipt for {record.key}")
            with self.hub_db:
                status = self.hub_db.execute(
                    "UPDATE queue SET state='acked' WHERE id=? AND state='inflight'",
                    (record.key,),
                ).rowcount
            if status:
                now = time.monotonic() - self.start
                self.receipt_time[record.key] = now
                self.log_record("hub_receipt", record, now)
            self.hub_pos += 1

    def ingest(self, record):
        with self.hub_db:
            self.hub_db.execute("INSERT INTO queue VALUES (?,?,?,?, 'queued')",
                                (record.key, record.kind, record.digest, record.body))
        self.log_record("hub_queue_commit", record, time.monotonic() - self.start)

    def choose(self):
        if self.policy == "fifo":
            return self.hub_db.execute(
                "SELECT id FROM queue WHERE state='queued' ORDER BY rowid LIMIT 1"
            ).fetchone()
        order = ("alert", "science", "status") if self.status_streak >= 3 else ("alert", "status", "science")
        for kind in order:
            row = self.hub_db.execute("SELECT id FROM queue WHERE state='queued' AND class=? "
                                      "ORDER BY rowid LIMIT 1", (kind,)).fetchone()
            if row:
                return row
        return None

    def dispatch_due(self, now):
        if now < self.next_send or now >= self.cutoff:
            return
        outstanding = self.hub_db.execute("SELECT count(*) FROM queue WHERE state='inflight'").fetchone()[0]
        if outstanding >= WINDOW:
            return
        row = self.choose()
        if row is None:
            return
        record = self.by_id[row[0]]
        wire_time = len(record.body) / RATE
        # Charge payload serialization time before another record can be submitted.
        if now + wire_time > self.cutoff:
            return
        filename = f"payload-{record.key}.json"
        (self.output / "hub" / filename).write_bytes(record.body)
        with self.hub_db:
            self.hub_db.execute("UPDATE queue SET state='inflight' WHERE id=?", (record.key,))
        submit(self.hub_sender, filename)
        sent_at = time.monotonic() - self.start
        self.next_send = sent_at + wire_time
        if record.kind != "alert":
            self.status_streak = self.status_streak + 1 if record.kind == "status" else 0
        self.log_record("hub_injected", record, sent_at)

    def log_record(self, name, record, now):
        self.event_stream.write(json.dumps({"event": name, "id": record.key, "class": record.kind,
                                             "bytes": len(record.body), "t_s": now}) + "\n")

    def loop(self):
        downlink = next(key for key in json.loads(docker(
            "inspect", "--format", "{{json .NetworkSettings.Networks}}", self.relay
        )) if key != self.network)
        self.delay_link(self.relay, self.network, HUB_DELAY)
        self.delay_link(self.relay, downlink, EARTH_DELAY)
        self.delay_link(self.earth, milliseconds=EARTH_DELAY)
        closed, earth_session = self.close()
        self.start = closed
        self.event("trace_started", policy=self.policy, trace_sha256=self.trace_digest,
                   planned_records=len(self.records), rise_s=self.rise, acquisition_complete_s=self.acquired,
                   cutoff_s=self.cutoff)
        cursor = 0
        ready = False
        opened = False
        geometric_rise = False
        closed_at_end = False
        next_report = 60
        while True:
            now = time.monotonic() - self.start
            if now >= self.cutoff and not closed_at_end:
                if not opened:
                    raise RuntimeError("Contact never opened")
                self.close()
                closed_at_end = True
                self.event("trace_cutoff", elapsed_s=now)
            while cursor < len(self.records) and self.records[cursor].due <= now:
                self.ingest(self.records[cursor])
                cursor += 1
            if now >= self.rise and not geometric_rise:
                geometric_rise = True
                self.event("geometric_rise", elapsed_s=now)
            if now >= self.acquired and not opened:
                if self.relay_removals() <= self.previous_relay_removals:
                    raise RuntimeError("Relay retained the old hub return route through acquisition")
                Bench.reopen(self, closed, earth_session, 0, set())
                self.delay_link(self.hub, milliseconds=HUB_DELAY)
                self.contact = True
                opened = True
            if opened and not ready and self.contact and self.ready():
                ready = True
                self.first_session = time.monotonic() - self.start
                self.event("fresh_hub_session", elapsed_s=self.first_session)
            if opened:
                self.poll_earth()
                self.poll_hub()
            if ready and self.contact:
                self.dispatch_due(time.monotonic() - self.start)
            if now >= next_report:
                counts = dict(self.hub_db.execute("SELECT state,count(*) FROM queue GROUP BY state"))
                self.event("trace_progress", elapsed_s=now, received=len(self.commit_time),
                           queue_counts=counts)
                next_report += 60
            if now >= self.cutoff + 5:
                break
            time.sleep(0.008 if opened else 0.08)

    def summarize(self):
        on_time = {key for key, at in self.commit_time.items() if at <= self.cutoff}
        receipts = {key for key, at in self.receipt_time.items() if at <= self.cutoff}
        counts = Counter(self.by_id[key].kind for key in on_time)
        total_bytes = sum(len(self.by_id[key].body) for key in on_time)
        alert_rows = {}
        for record in self.records:
            if record.kind == "alert":
                latency = self.commit_time[record.key] - record.due if record.key in on_time else None
                alert_rows[record.key] = {"latency_s": latency, "deadline_met": latency is not None and latency <= 10}
        summary = {
            "policy": self.policy, "rehearsal": self.rehearsal, "trace_jsonl_sha256": self.trace_digest,
            "cutoff_s": self.cutoff, "usable_s": self.cutoff - self.acquired,
            "first_tcpcl_session_s": self.first_session, "outstanding_limit": WINDOW,
            "pacing_bytes_per_s": RATE, "one_way_hop_delay_ms": [HUB_DELAY, EARTH_DELAY],
            "offered_records": len(self.records), "earth_records": len(on_time),
            "earth_records_by_class": dict(counts), "earth_payload_bytes": total_bytes,
            "mean_payload_goodput_kib_s": total_bytes / (self.cutoff - self.acquired) / 1024,
            "earth_undelivered_bytes": sum(len(r.body) for r in self.records if r.key not in on_time),
            "hub_unconfirmed_bytes": sum(len(r.body) for r in self.records if r.key not in receipts),
            "hub_receipts": len(receipts), "alerts": alert_rows,
            "duplicate_earth_arrivals": sum(count - 1 for count in self.arrivals.values()),
            "post_cutoff_earth_records": len(self.commit_time) - len(on_time),
            "no_session_transfer_failures": self.failure_count(),
        }
        (self.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        self.event("trace_summary", **summary)

    def run(self):
        for node, endpoint in ((self.hub, "ipn:10.2"), (self.earth, "ipn:30.1")):
            docker("exec", "-d", "-w", "/run/ion", node, "bprecvfile", endpoint)
        with ExitStack() as stack:
            self.event_stream = stack.enter_context((self.output / "records.jsonl").open("w", buffering=1))
            self.hub_db = stack.enter_context(sqlite3.connect(self.output / "hub-queue.sqlite3"))
            self.earth_db = stack.enter_context(sqlite3.connect(self.output / "earth-ledger.sqlite3"))
            self.hub_db.execute("PRAGMA synchronous=FULL")
            self.earth_db.execute("PRAGMA synchronous=FULL")
            self.hub_db.execute("CREATE TABLE queue (id TEXT PRIMARY KEY,class TEXT, sha256 TEXT, "
                                "payload BLOB, state TEXT)")
            self.earth_db.execute("CREATE TABLE records (id TEXT PRIMARY KEY, sha256 TEXT, payload BLOB)")
            hub_log = stack.enter_context((self.output / "hub-sender.log").open("w"))
            earth_log = stack.enter_context((self.output / "earth-sender.log").open("w"))
            self.hub_sender = sender(self.hub, "ipn:10.1", "ipn:30.1", hub_log)
            self.earth_sender = sender(self.earth, "ipn:30.2", "ipn:10.2", earth_log)
            try:
                self.loop()
                self.summarize()
            finally:
                for worker in (self.hub_sender, self.earth_sender):
                    worker.stdin.close()
                    try:
                        worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        worker.kill()
                        worker.wait()


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit("Usage: trace.py OUT UPLINK HUB RELAY EARTH")
    Replay(*sys.argv[1:]).run()
