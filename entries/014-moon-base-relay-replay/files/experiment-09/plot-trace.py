#!/usr/bin/env python3
"""Render the live BPv7 policy comparison from the recorded event streams."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_run(path):
    summary = json.loads((path / "summary.json").read_text())
    with (path / "records.jsonl").open() as stream:
        return summary, [json.loads(line) for line in stream]


def steps(events, start, end, increments):
    total = 0
    x, y = [], []
    for event in events:
        elapsed = event["t_s"]
        if elapsed > end:
            break
        if event["event"] not in increments:
            continue
        if elapsed >= start and not x:
            x.append(start)
            y.append(total / 1024)
        total += increments[event["event"]] * event["bytes"]
        if elapsed >= start:
            x.append(elapsed)
            y.append(total / 1024)
    if not x:
        x, y = [start], [total / 1024]
    return x + [end], y + [total / 1024]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fifo", type=Path)
    parser.add_argument("alerts_first", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    runs = [read_run(path) for path in (args.fifo, args.alerts_first)]
    cutoff = runs[0][0]["cutoff_s"]
    acquired = cutoff - runs[0][0]["usable_s"]
    rise = acquired - 30
    if any(summary["rehearsal"] or summary["cutoff_s"] != cutoff for summary, _ in runs):
        raise SystemExit("Provide two matching full replay runs")
    styles = [("FIFO", "#244d7c", "-"), ("Alerts first", "#b34822", "--")]
    figure, axes = plt.subplots(2, 2, figsize=(12, 7.5), layout="constrained")
    backlog, delivery, pending, alerts = axes.flat
    for axis in (backlog, delivery, pending):
        axis.axvspan(0, rise / 60, color="#eaeef3")
        axis.axvspan(rise / 60, acquired / 60, color="#f3dda3")
        axis.axvspan(acquired / 60, cutoff / 60, color="#e1eee5")
        axis.set_xlabel("Minutes since outage began")
    for (summary, events), (label, color, line) in zip(runs, styles):
        for axis, start, increments in (
            (backlog, 0, {"hub_queue_commit": 1, "hub_injected": -1}),
            (delivery, rise, {"earth_commit": 1}),
            (pending, rise, {"hub_injected": 1, "hub_receipt": -1}),
        ):
            x, y = steps(events, start, cutoff, increments)
            axis.step([t / 60 for t in x], y, where="post", color=color,
                      linestyle=line, linewidth=1.7, label=label)
            axis.set_xlim(start / 60, cutoff / 60)
    backlog.set(title="Backlog waiting to enter ION", ylabel="KiB")
    delivery.set(title="Unique payload committed at Earth", ylabel="KiB")
    pending.set(title="Sent payload awaiting Earth receipt", ylabel="KiB")
    backlog.legend(loc="upper left")
    keys = ("alert-outage", "alert-contact-open", "alert-pass-close")
    for i, ((summary, _), (label, color, _)) in enumerate(zip(runs, styles)):
        for j, key in enumerate(keys):
            latency = summary["alerts"][key]["latency_s"]
            x = j + (i - 0.5) * 0.26
            if latency is None:
                alerts.plot(x, 2400, marker="x", color=color, markersize=7)
            else:
                alerts.plot(x, latency, marker="o", color=color, markersize=7)
                alerts.annotate(f"{latency:.1f}s", (x, latency), xytext=(0, 8),
                                textcoords="offset points", ha="center", fontsize=8, color=color)
    alerts.axhline(10, linestyle=":", color="#333333", label="10 s deadline")
    alerts.set(title="Alert latency to Earth commit", ylabel="Seconds (log scale)", yscale="log",
               ylim=(1, 4200), xlim=(-0.45, 2.45), xticks=range(3),
               xticklabels=("During outage", "At opening", "Near cutoff"))
    if any(alert["latency_s"] is None for summary, _ in runs for alert in summary["alerts"].values()):
        alerts.text(0.985, 0.98, "×  No commit by cutoff", transform=alerts.transAxes,
                    ha="right", va="top", fontsize=9)
    alerts.legend(loc="center right", bbox_to_anchor=(0.99, 0.40))
    figure.suptitle("Live BPv7 stack replay with emulated relay contacts", fontsize=16)
    figure.savefig(args.output, dpi=160)


if __name__ == "__main__":
    main()
