#!/usr/bin/env python3
"""Export one existing LTE intake row as a byte-stable JSON bundle payload."""
import argparse
import json
from pathlib import Path
import re
import sqlite3

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("database", type=Path)
parser.add_argument("expected_body")
parser.add_argument("output", type=Path)
args = parser.parse_args()
with sqlite3.connect(f"file:{args.database}?mode=ro", uri=True) as db:
    rows = db.execute("SELECT id,body,queued_at FROM messages WHERE body=?", (args.expected_body,)).fetchall()
if len(rows) != 1:
    raise SystemExit(f"Expected one row, found {len(rows)}")
record_id, body, queued_at = rows[0]
if not re.fullmatch("[0-9a-f]{32}", record_id):
    raise SystemExit("Unexpected store_forward record ID")
args.output.write_text(json.dumps({"id": record_id, "body": body, "queued_at": queued_at},
                                  sort_keys=True, separators=(",", ":")) + "\n")
print(record_id)
