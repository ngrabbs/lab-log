#!/usr/bin/env python3
"""Replay a deterministic rover telemetry workload over scheduled relay contacts."""

import argparse
from collections import deque
from dataclasses import dataclass
import csv
import gzip
import hashlib
import heapq
import io
from itertools import count
import json
from pathlib import Path

SECOND = 1_000_000
WINDOWS_S = ((1800, 1830, 2100), (3900, 3930, 4200))
USABLE = tuple((start * SECOND, end * SECOND) for _, start, end in WINDOWS_S)
CUTOFF = USABLE[0][1]
END = USABLE[-1][1]
HUB_RATE = 10 * 1024
RELAY_RATE = 100 * 1024
HUB_DELAY = 50_000
RELAY_DELAY = 1_250_000
ALERT_DEADLINE_MS = 10_000
RETRY_TIMEOUT = 8 * SECOND
CLASSES = ("alert", "status", "science")
LOST_RECORD = "alert-pass-close"


@dataclass(frozen=True)
class Record:
    id: str
    kind: str
    at_ms: int
    size: int
    sha256: str

    @property
    def at(self):
        return self.at_ms * 1000


def encode(fields):
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def generate_trace(path):
    duration_s = END // SECOND
    events = [
        (t * 1000, f"status-{t // 2:04}", "status", 512,
         {"battery_mv": 12180 - (t % 320), "temp_c_x100": 2250 + (t % 100)})
        for t in range(0, duration_s, 2)
    ]
    events.extend(
        (t * 1000, f"science-{t // 4:04}", "science", 3072,
         {"product": "thermal-tile", "chunk": t // 4})
        for t in range(0, duration_s, 4)
    )
    events.extend([
        (900_000, "alert-outage", "alert", 128, {"code": "BATTERY_LOW"}),
        (1_830_050, "alert-contact-open", "alert", 128, {"code": "BATTERY_LOW"}),
        (2_095_000, LOST_RECORD, "alert", 128, {"code": "BATTERY_LOW"}),
    ])
    with (path.open("wb") as raw,
          gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
          io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as trace):
        for at_ms, record_id, kind, size, values in sorted(events):
            payload = {"v": 1, "id": record_id, "t_ms": at_ms, "class": kind,
                       **values, "data": ""}
            if kind == "alert":
                payload["deadline_ms"] = at_ms + ALERT_DEADLINE_MS
            remaining = size - len(encode(payload))
            if remaining < 0:
                raise ValueError(f"Record metadata exceeds {size} bytes: {record_id}")
            payload["data"] = hashlib.shake_256(record_id.encode()).hexdigest(
                (remaining + 1) // 2
            )[:remaining]
            text = encode(payload)
            trace.write(encode({"payload": text, "sha256": hashlib.sha256(
                text.encode()
            ).hexdigest()}) + "\n")


def read_trace(path):
    records = []
    ids = set()
    with gzip.open(path, "rt", encoding="utf-8") as trace:
        for line in trace:
            row = json.loads(line)
            payload = row["payload"].encode()
            values = json.loads(payload)
            if hashlib.sha256(payload).hexdigest() != row["sha256"]:
                raise ValueError(f"Payload hash mismatch: {values['id']}")
            if values["id"] in ids:
                raise ValueError(f"Duplicate trace ID: {values['id']}")
            ids.add(values["id"])
            records.append(Record(values["id"], values["class"], values["t_ms"],
                                  len(payload), row["sha256"]))
    return records


def serial_time(size, rate):
    return (size * SECOND + rate - 1) // rate


def return_arrival(earth_commit):
    ready = earth_commit + RELAY_DELAY
    for start, end in USABLE:
        arrival = max(ready, start) + HUB_DELAY
        if arrival <= end:
            return arrival
    return None


class Replay:
    def __init__(self, records, alerts_first=False, suppress_receipt=False):
        self.records = records
        self.alerts_first = alerts_first
        self.suppress_receipt = suppress_receipt
        self.events = []
        self.sequence = count()
        self.hub = {kind: deque() for kind in (*CLASSES, "fifo")}
        self.relay = deque()
        self.hub_bytes = self.relay_bytes = 0
        self.hub_free = self.relay_free = 0
        self.status_streak = 0
        self.ledger = {}
        self.confirmed = set()
        self.arrivals = []
        self.log = []
        self.queue = [(0, 0, 0)]
        for record in records:
            self.schedule(record.at, "generate", record)
        for start, _ in USABLE:
            self.schedule(start, "contact_open")

    def schedule(self, now, event, record=None):
        if now <= END:
            heapq.heappush(self.events, (now, next(self.sequence), event, record))

    def enqueue(self, record):
        queue = self.hub[record.kind if self.alerts_first else "fifo"]
        queue.append(record)
        self.hub_bytes += record.size

    def record_event(self, now, event, record):
        self.log.append((now, event, record.id, record.kind))

    def hub_send(self, now):
        if now < self.hub_free:
            return
        end = next((end for start, end in USABLE if start <= now < end), now)
        if end == now:
            return
        if not self.alerts_first:
            queue = self.hub["fifo"]
        elif self.hub["alert"]:
            queue = self.hub["alert"]
        elif self.hub["status"] and (not self.hub["science"] or self.status_streak < 3):
            queue = self.hub["status"]
        else:
            queue = self.hub["science"]
        if not queue:
            return
        record = queue[0]
        finish = now + serial_time(record.size, HUB_RATE)
        if finish + HUB_DELAY > end:
            return
        queue.popleft()
        self.hub_bytes -= record.size
        if self.alerts_first and record.kind != "alert":
            self.status_streak = self.status_streak + 1 if record.kind == "status" else 0
        self.hub_free = finish
        self.schedule(finish, "link_ready")
        self.schedule(finish + HUB_DELAY, "relay_arrival", record)
        self.record_event(now, "hub_send", record)
        if self.suppress_receipt and record.id == LOST_RECORD and record.id not in self.ledger:
            self.schedule(now + RETRY_TIMEOUT, "receipt_timeout", record)

    def relay_send(self, now):
        if not self.relay or now < self.relay_free:
            return
        record = self.relay.popleft()
        self.relay_bytes -= record.size
        self.relay_free = now + serial_time(record.size, RELAY_RATE)
        self.schedule(self.relay_free, "link_ready")
        self.schedule(self.relay_free + RELAY_DELAY, "earth_arrival", record)

    def earth_arrival(self, now, record):
        self.arrivals.append((now, record.id))
        previous = self.ledger.get(record.id)
        if previous is None:
            self.ledger[record.id] = (now, record)
            self.record_event(now, "earth_commit", record)
            if self.suppress_receipt and record.id == LOST_RECORD:
                self.record_event(now, "receipt_suppressed", record)
                return
        else:
            if previous[1].sha256 != record.sha256:
                raise ValueError(f"Record ID reused with different payload: {record.id}")
            self.record_event(now, "earth_duplicate", record)
        receipt = return_arrival(now)
        if receipt is not None:
            self.schedule(receipt, "receipt", record)

    def run(self):
        while self.events:
            now = self.events[0][0]
            while self.events and self.events[0][0] == now:
                _, _, event, record = heapq.heappop(self.events)
                match event:
                    case "generate":
                        self.enqueue(record)
                    case "relay_arrival":
                        self.relay.append(record)
                        self.relay_bytes += record.size
                        self.record_event(now, event, record)
                    case "earth_arrival":
                        self.earth_arrival(now, record)
                    case "receipt":
                        self.confirmed.add(record.id)
                        self.record_event(now, event, record)
                    case "receipt_timeout":
                        if record.id not in self.confirmed:
                            self.enqueue(record)
                            self.record_event(now, "retry_queued", record)
            self.hub_send(now)
            self.relay_send(now)
            if self.queue[-1][1:] != (self.hub_bytes, self.relay_bytes):
                self.queue.append((now, self.hub_bytes, self.relay_bytes))
        return self

    def summary(self):
        offered = [record for record in self.records if record.at < CUTOFF]
        commits = [record for at, record in self.ledger.values() if at <= CUTOFF]
        alerts = {}
        for record in offered:
            if record.kind == "alert":
                commit = self.ledger.get(record.id)
                latency = None if commit is None else (commit[0] - record.at) / SECOND
                alerts[record.id] = {
                    "latency_s": latency,
                    "met_deadline": latency is not None and latency <= ALERT_DEADLINE_MS / 1000,
                }
        status_ages = sorted(
            at - record.at for at, record in self.ledger.values()
            if at <= CUTOFF and record.kind == "status"
        )
        queue_at_close = next(row[1] for row in reversed(self.queue) if row[0] < CUTOFF)
        return {
            "offered_records_by_first_close": len(offered),
            "offered_bytes_by_first_close": sum(record.size for record in offered),
            "earth_records_by_first_close": len(commits),
            "earth_bytes_by_first_close": sum(record.size for record in commits),
            "earth_records_by_class": {
                kind: sum(record.kind == kind for record in commits) for kind in CLASSES
            },
            "peak_hub_queue_bytes_first_pass": max(hub for at, hub, _ in self.queue if at <= CUTOFF),
            "hub_queue_bytes_at_first_close": queue_at_close,
            "peak_relay_waiting_bytes_first_pass": max(relay for at, _, relay in self.queue if at <= CUTOFF),
            "status_age_p95_s": status_ages[(95 * len(status_ages) - 1) // 100] / SECOND
            if status_ages else None,
            "alerts": alerts,
            "duplicate_arrivals_full_run": len(self.arrivals) - len(self.ledger),
            "target_events": [
                {"time_s": at / SECOND, "event": event}
                for at, event, record_id, _ in self.log if record_id == LOST_RECORD
            ],
        }


def plot_results(out, runs, summaries):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"fifo": "#315d95", "alerts_first": "#a84315"}
    labels = {"fifo": "FIFO", "alerts_first": "Alerts first"}
    fig, (queue, earth, alerts) = plt.subplots(
        3, 1, figsize=(10, 9), layout="constrained", height_ratios=(1, 1, 0.8)
    )
    for ax in (queue, earth):
        ax.axvspan(0, 30, color="#eceef1", label="Closed")
        ax.axvspan(30, 30.5, color="#f4dfa9", label="Acquisition")
        ax.axvspan(30.5, 35, color="#e2eee3", label="Usable contact")
        ax.set_xlim(0, 35)
    for name in ("fifo", "alerts_first"):
        run = runs[name]
        points = [(t, hub) for t, hub, _ in run.queue if t < CUTOFF]
        points.append((CUTOFF, points[-1][1]))
        ts, depths = zip(*points)
        style = "--" if name == "alerts_first" else "-"
        queue.step([t / (60 * SECOND) for t in ts], [v / 1024 for v in depths],
                   where="post", color=colors[name], linestyle=style, label=labels[name])
        cumulative = 0
        times = [0]
        payload = [0]
        for at, record in run.ledger.values():
            if at <= CUTOFF:
                cumulative += record.size
                times.append(at / (60 * SECOND))
                payload.append(cumulative / 1024)
        earth.step(times + [35], payload + [payload[-1]], where="post",
                   color=colors[name], linestyle=style, label=labels[name])
    relay = [(t / (60 * SECOND), size / 1024) for t, _, size in runs["fifo"].queue
             if t < CUTOFF]
    if any(size for _, size in relay):
        queue.step(*zip(*relay), where="post", linestyle=":", color="#485448",
                   label="Relay (FIFO)")
    queue.set(title="Queued payload at the hub", ylabel="Queue (KiB)")
    queue.legend(ncols=3, loc="upper left")
    earth.set(title="Unique payload durably received at Earth", ylabel="Delivered (KiB)",
              xlabel="Minutes since outage began")
    alert_ids = ("alert-outage", "alert-contact-open", LOST_RECORD)
    for i, name in enumerate(("fifo", "alerts_first")):
        latencies = [summaries[name]["alerts"][key]["latency_s"] for key in alert_ids]
        positions = [j + (i - 0.5) * 0.34 for j in range(3)]
        bars = alerts.bar(positions, latencies, width=0.30, color=colors[name], label=labels[name])
        alerts.bar_label(bars, labels=[f"{s:.2f} s" for s in latencies], padding=3)
    alerts.axhline(10, color="#262626", linestyle="--", label="10 s deadline")
    alerts.set(title="Earth commit latency by alert", ylabel="Seconds (log scale)",
               ylim=(1, 2500), yscale="log",
               xticks=range(3), xticklabels=["During outage", "At acquisition", "Near pass close"])
    alerts.legend(ncols=3, loc="upper right")
    fig.suptitle("Simulated telemetry replay across the first relay pass", fontsize=15)
    fig.savefig(out / "queue-and-delivery.png", dpi=170)
    plt.close(fig)

    target = summaries["lost_receipt"]["target_events"]
    time_for = {item["event"]: item["time_s"] for item in target}
    fig, (first, second) = plt.subplots(1, 2, sharey=True, figsize=(10, 3.7), layout="constrained")
    rows = {"receipt_suppressed": 2, "retry_queued": 1, "earth_duplicate": 2, "receipt": 0}
    for ax, keys, reference, title in (
        (first, ("receipt_suppressed", "retry_queued"), 2100, "First pass closes"),
        (second, ("earth_duplicate", "receipt"), 3930, "Next usable contact opens"),
    ):
        ax.axvline(0, color="#696969", linestyle="--")
        for key in keys:
            x = time_for[key] - reference
            ax.scatter(x, rows[key], s=65, color="#315d95" if ax is first else "#a84315")
            ax.annotate(f"t={time_for[key]:.3f} s", (x, rows[key]), xytext=(0, 9),
                        textcoords="offset points", ha="center")
        ax.set(title=title, xlabel="Seconds relative to contact boundary", xlim=(-5, 5), ylim=(-0.5, 2.7))
    first.set(yticks=[0, 1, 2], yticklabels=["Hub confirms receipt", "Hub queues retry", "Earth arrival"])
    fig.suptitle("Lost receipt replay | one Earth commit and one duplicate arrival", fontsize=14)
    fig.savefig(out / "lost-receipt.png", dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("output"))
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    trace = out / "telemetry.jsonl.gz"
    generate_trace(trace)
    records = read_trace(trace)
    runs = {
        "fifo": Replay(records).run(),
        "alerts_first": Replay(records, alerts_first=True).run(),
        "lost_receipt": Replay(records, alerts_first=True, suppress_receipt=True).run(),
    }
    summaries = {name: run.summary() for name, run in runs.items()}
    with gzip.open(trace, "rb") as stream:
        trace_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {
        "configuration": {
            "contact_windows_s_rise_usable_close": WINDOWS_S,
            "hub_payload_rate_Bps": HUB_RATE,
            "relay_payload_rate_Bps": RELAY_RATE,
            "hub_delay_ms": HUB_DELAY / 1000,
            "relay_delay_ms": RELAY_DELAY / 1000,
            "alert_deadline_ms": ALERT_DEADLINE_MS,
            "injected_retry_timeout_s": RETRY_TIMEOUT / SECOND,
            "trace_records": len(records),
            "trace_jsonl_sha256": trace_digest,
        },
        "runs": summaries,
    }
    (out / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (out / "events.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("run", "sim_time_s", "event", "record_id", "class"))
        for name, run in runs.items():
            writer.writerows((name, at / SECOND, event, key, kind)
                             for at, event, key, kind in run.log)
    with (out / "queues.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("run", "sim_time_s", "hub_waiting_bytes", "relay_waiting_bytes"))
        for name, run in runs.items():
            writer.writerows((name, at / SECOND, hub, relay) for at, hub, relay in run.queue)
    plot_results(out, runs, summaries)
    print(f"Trace: {len(records)} records, JSONL SHA-256 {trace_digest}")
    for name, result in summaries.items():
        print(f"{name}: {result['earth_records_by_first_close']}/"
              f"{result['offered_records_by_first_close']} unique Earth records by first close"
              f" ({result['earth_bytes_by_first_close']:,} B); "
              f"{sum(a['met_deadline'] for a in result['alerts'].values())}/3 alerts on time; "
              f"{result['duplicate_arrivals_full_run']} repeated arrivals over both passes")
    for item in summaries["lost_receipt"]["target_events"]:
        print(f"{item['time_s']:.6f} s  {item['event']}")


if __name__ == "__main__":
    main()
