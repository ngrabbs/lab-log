#!/usr/bin/env python3
"""Independently reconcile live trace events, SQLite ledgers, and cutoff metrics."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
from statistics import median


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_jsonl(path):
    with path.open() as stream:
        return [json.loads(line) for line in stream]


def validate(run, trace):
    summary = json.loads((run / "summary.json").read_text())
    events = read_jsonl(run / "records.jsonl")
    timeline = read_jsonl(run / "timeline.jsonl")
    require(not summary["rehearsal"], "Provide full trace runs")
    require(hashlib.sha256(trace).hexdigest() == summary["trace_jsonl_sha256"], "Trace digest mismatch")
    cutoff = summary["cutoff_s"]
    input_payloads = {}
    for row in map(json.loads, trace.splitlines()):
        payload = row["payload"].encode()
        fields = json.loads(payload)
        if fields["t_ms"] / 1000 < cutoff:
            input_payloads[fields["id"]] = payload
    with sqlite3.connect(f"file:{run / 'earth-ledger.sqlite3'}?mode=ro", uri=True) as earth:
        rows = {record: (digest, payload) for record, digest, payload in earth.execute(
            "SELECT id,sha256,payload FROM records")}
    with sqlite3.connect(f"file:{run / 'hub-queue.sqlite3'}?mode=ro", uri=True) as hub:
        queued = dict(hub.execute("SELECT id,payload FROM queue"))
    require(queued == input_payloads, "Hub spool does not match input trace")
    require(all(body == input_payloads[key] and hashlib.sha256(body).hexdigest() == digest
                for key, (digest, body) in rows.items()), "Earth database payload mismatch")
    commits = [e for e in events if e["event"] == "earth_commit"]
    commit_ids = [e["id"] for e in commits]
    require(len(commit_ids) == len(rows) and set(commit_ids) == rows.keys(), "Earth commit event mismatch")
    acquisition_complete = cutoff - summary["usable_s"]
    require(all(e["t_s"] >= acquisition_complete for e in commits), "Unexpected Earth commit during cut")
    by_cutoff = [e for e in commits if e["t_s"] <= cutoff]
    committed = {e["id"] for e in by_cutoff}
    receipts = {e["id"] for e in events if e["event"] == "hub_receipt" and e["t_s"] <= cutoff}
    require(receipts <= committed, "Receipt without earlier Earth commit")
    pending = set()
    peak = 0
    full_time = 0
    previous = acquisition_complete
    submissions = {}
    receipt_age = []
    for event in events:
        timestamp = event["t_s"]
        if acquisition_complete <= timestamp <= cutoff:
            if len(pending) == summary["outstanding_limit"]:
                full_time += timestamp - previous
            previous = timestamp
        if event["event"] == "hub_injected":
            require(event["id"] not in pending, "Unexpected repeated submission")
            pending.add(event["id"])
            submissions[event["id"]] = timestamp
            peak = max(peak, len(pending))
        elif event["event"] == "hub_receipt":
            pending.remove(event["id"])
            if timestamp <= cutoff:
                receipt_age.append(timestamp - submissions[event["id"]])
    # Use the state at the cutoff even if more receipts are observed afterward.
    if len(set(submissions) - receipts) == summary["outstanding_limit"]:
        full_time += cutoff - previous
    require(peak <= summary["outstanding_limit"], "In-flight limit exceeded")
    require(len(input_payloads) == summary["offered_records"], "Offered count mismatch")
    require(len(by_cutoff) == summary["earth_records"], "Earth cutoff count mismatch")
    require(dict(Counter(e["class"] for e in by_cutoff)) == summary["earth_records_by_class"],
            "Per-class Earth cutoff counts mismatch")
    require(sum(len(input_payloads[key]) for key in committed) == summary["earth_payload_bytes"],
            "Delivered byte mismatch")
    require(sum(len(body) for key, body in input_payloads.items() if key not in committed)
            == summary["earth_undelivered_bytes"], "Earth backlog byte mismatch")
    require(len(receipts) == summary["hub_receipts"], "Cutoff receipt count mismatch")
    require(sum(len(body) for key, body in input_payloads.items() if key not in receipts)
            == summary["hub_unconfirmed_bytes"], "Hub backlog byte mismatch")
    require(sum(e["event"] == "earth_duplicate" for e in events) == summary["duplicate_earth_arrivals"],
            "Duplicate arrival count mismatch")
    require(len(rows) - len(by_cutoff) == summary["post_cutoff_earth_records"], "Late arrival count mismatch")
    require(sum("no TCPCL session, failing xfer" in line for line in (run / "hub-active.log").open())
            == summary["no_session_transfer_failures"], "TCPCL failure count mismatch")
    first_cut, final_cut = [event for event in timeline if event["event"] == "uplink_closed"]
    require(first_cut["earth_session"] == final_cut["earth_session"], "Earth session changed")
    print(f"{summary['policy']}: reconciled {len(rows)} ledger rows, {len(by_cutoff)} at cutoff, "
          f"{len(receipts)} receipts at cutoff, peak outstanding {peak}")
    if receipt_age:
        print(f"  Window full for {full_time:.1f} s of {summary['usable_s']} s. "
              f"Median submission-to-receipt {median(receipt_age):.2f} s.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("fifo", type=Path)
    parser.add_argument("alerts_first", type=Path)
    args = parser.parse_args()
    with gzip.open(args.trace, "rb") as stream:
        trace = stream.read()
    fifo = validate(args.fifo, trace)
    priority = validate(args.alerts_first, trace)
    require((fifo["policy"], priority["policy"]) == ("fifo", "alerts-first"), "Wrong comparison order")
    keys = ("cutoff_s", "usable_s", "trace_jsonl_sha256", "outstanding_limit",
            "pacing_bytes_per_s", "one_way_hop_delay_ms")
    require(all(fifo[key] == priority[key] for key in keys), "Runs differ in more than policy")


if __name__ == "__main__":
    main()
