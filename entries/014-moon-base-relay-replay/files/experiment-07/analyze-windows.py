#!/usr/bin/env python3
"""Match exact synthetic ADU bytes in relay pcap streams and application logs."""
import argparse
from bisect import bisect_right
from collections import defaultdict
import csv
import gzip
import json
from pathlib import Path
import re
from statistics import median
import struct

ID = re.compile(rb'"id"\s*:\s*"([a-z0-9-]+)"')
STAGES = ("hub_injected", "relay_rx", "relay_tx", "earth_commit",
          "earth_receipt_submitted", "relay_receipt_rx", "relay_receipt_tx", "hub_receipt")


def tcp_segments(path):
    flows = defaultdict(list)
    with path.open("rb") as stream:
        magic = stream.read(4)
        order, scale = {
            b"\xd4\xc3\xb2\xa1": ("<", 1000), b"\xa1\xb2\xc3\xd4": (">", 1000),
            b"\x4d\x3c\xb2\xa1": ("<", 1), b"\xa1\xb2\x3c\x4d": (">", 1),
        }[magic]
        header = stream.read(20)
        if struct.unpack_from(order + "I", header, 16)[0] & 0xFFFF != 1:
            raise ValueError(f"Expected Ethernet link type in {path}")
        while header := stream.read(16):
            sec, subsec, captured, _ = struct.unpack(order + "IIII", header)
            frame = stream.read(captured)
            if len(frame) < 54 or frame[12:14] != b"\x08\x00" or frame[23] != 6:
                continue
            ip = 14
            tcp = ip + (frame[ip] & 15) * 4
            if len(frame) < tcp + 20:
                continue
            src, dst = frame[ip+12:ip+16], frame[ip+16:ip+20]
            sport, dport, seq = struct.unpack_from("!HHI", frame, tcp)
            total = struct.unpack_from("!H", frame, ip + 2)[0]
            data = frame[tcp + (frame[tcp + 12] >> 4) * 4:ip + total]
            if data:
                flows[src, dst, sport, dport].append((seq, sec * 10**9 + subsec * scale, data))
    return flows


def contiguous_blocks(segments):
    # Normalise sequence numbers including the 32-bit rollover.
    base = segments[0][0]
    entries = sorted((((seq - base + 2**31) % 2**32) - 2**31, timestamp, data)
                     for seq, timestamp, data in segments)
    begin = end = entries[0][0]
    data = bytearray()
    ends = []
    times = []
    for offset, timestamp, chunk in entries:
        if offset > end:
            yield data, ends, times
            begin = end = offset
            data, ends, times = bytearray(), [], []
        take = end - offset
        if take < len(chunk):
            data.extend(chunk[take:])
            end = offset + len(chunk)
            ends.append(end - begin)
            times.append(timestamp)
    yield data, ends, times


def wire_times(run, relay_ips, origin, messages):
    seen = defaultdict(dict)
    for link, relay_ip in relay_ips.items():
        relay = bytes(int(octet) for octet in relay_ip.split("."))
        for (src, dst, _, _), segments in tcp_segments(run / f"{link}.pcap").items():
            if (src == relay) == (dst == relay):
                continue
            if link == "uplink":
                stage = "relay_receipt_tx" if src == relay else "relay_rx"
            else:
                stage = "relay_tx" if src == relay else "relay_receipt_rx"
            msg_kind = int("receipt" in stage)
            for data, ends, times in contiguous_blocks(segments):
                for match in ID.finditer(data):
                    key = match[1].decode()
                    if key not in messages:
                        continue
                    payload, key_at = messages[key][msg_kind]
                    start = match.start() - key_at
                    end = start + len(payload)
                    if start < 0 or data[start:end] != payload:
                        continue
                    mark = (max(times[bisect_right(ends, start):bisect_right(ends, end - 1) + 1])
                            - origin) / 1e9
                    if stage not in seen[key] or mark < seen[key][stage]:
                        seen[key][stage] = mark
    return seen


def analyze(run, trace, output):
    summary = json.loads((run / "summary.json").read_text())
    timeline = [json.loads(line) for line in (run / "timeline.jsonl").read_text().splitlines()]
    start = next(row for row in timeline if row["event"] == "trace_started")
    relay_ips = {row["role"]: row["relay_ip"] for row in timeline if row["event"] == "relay_capture"}
    matching = wire_times(run, relay_ips, start["wall_start_ns"], trace)
    classes = {}
    for line in (run / "records.jsonl").read_text().splitlines():
        event = json.loads(line)
        key = event["id"]
        classes[key] = event["class"]
        if event["event"] in STAGES:
            matching[key].setdefault(event["event"], event["t_s"])
    all_received = [row for row in matching.values()
                    if row.get("hub_receipt", float("inf")) <= summary["cutoff_s"]]
    complete = [row for row in all_received if all(stage in row for stage in STAGES)]
    if not complete or len(complete) < 0.95 * len(all_received):
        raise ValueError(f"{run}: insufficient trace matches ({len(complete)}/{len(all_received)})")
    for row in complete:
        if any(row[after] < row[before] - 0.005 for before, after in zip(STAGES, STAGES[1:])):
            raise ValueError(f"Relay and application clocks disagree: {row}")
    with (output / f"w{summary['outstanding_limit']}-stages.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("id", "class", *STAGES))
        for key, stages in matching.items():
            if "hub_injected" in stages:
                writer.writerow((key, classes[key], *(stages.get(stage) for stage in STAGES)))
    sample = matching["science-0000"]
    if not all(stage in sample for stage in STAGES) or sample["hub_receipt"] >= 43:
        raise ValueError("Single-record probe did not complete before backlog release")
    loaded = [row for row in complete if row["hub_injected"] >= 43]
    peak = 0
    pending = set()
    for line in (run / "records.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event["event"] == "hub_injected":
            pending.add(event["id"])
            peak = max(peak, len(pending))
        elif event["event"] == "hub_receipt":
            pending.remove(event["id"])
    if peak > summary["outstanding_limit"] or summary["no_session_transfer_failures"]:
        raise ValueError("Window or session gate regression")
    sci_bytes = len(trace["science-0000"][0][0])
    load_seconds = summary["cutoff_s"] - 43
    submitted = [row for row in matching.values() if 43 <= row.get("hub_injected", -1) <= summary["cutoff_s"]]
    unconfirmed = [row for row in submitted if row.get("hub_receipt", float("inf")) > summary["cutoff_s"]]
    result = {
        "window": summary["outstanding_limit"], "peak_outstanding": peak,
        "loaded_seconds": load_seconds,
        "loaded_earth_records": summary["earth_records"] - 1,
        "loaded_payload_kib_s": (summary["earth_payload_bytes"] - sci_bytes) / load_seconds / 1024,
        "loaded_submissions": len(submitted), "loaded_receipts": len(submitted) - len(unconfirmed),
        "oldest_unconfirmed_s": max((summary["cutoff_s"] - row["hub_injected"]
                                     for row in unconfirmed), default=0),
        "fully_matched_credits": len(complete), "cutoff_credits": len(all_received),
        "single_record_s": sample["hub_receipt"] - sample["hub_injected"],
        "loaded_median_receipt_s": median(row["hub_receipt"] - row["hub_injected"] for row in loaded),
        "single_stages_s": {b: sample[b] - sample[a] for a, b in zip(STAGES, STAGES[1:])},
        "loaded_median_stages_s": {b: median(row[b] - row[a] for row in loaded)
                                   for a, b in zip(STAGES, STAGES[1:])},
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("runs", type=Path, nargs=3)
    args = parser.parse_args()
    trace = {}
    with gzip.open(args.trace, "rt") as stream:
        for line in stream:
            record = json.loads(line)
            body = record["payload"].encode()
            key = json.loads(body)["id"]
            receipt = json.dumps({"id": key, "sha256": record["sha256"],
                                  "disposition": "committed"}).encode()
            trace[key] = [(payload, ID.search(payload).start()) for payload in (body, receipt)]
    args.output.mkdir(parents=True, exist_ok=True)
    results = sorted((analyze(run, trace, args.output) for run in args.runs), key=lambda row: row["window"])
    text = json.dumps(results, indent=2) + "\n"
    (args.output / "comparison.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
