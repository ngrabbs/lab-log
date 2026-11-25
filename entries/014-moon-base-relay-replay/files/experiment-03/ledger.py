#!/usr/bin/env python3
"""Commit an Experiment 3 payload and optionally issue its receipt."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("payload", type=Path)
parser.add_argument("expected_hash")
parser.add_argument("--suppress-receipt", action="store_true")
args = parser.parse_args()
payload = args.payload.read_bytes()
digest = hashlib.sha256(payload).hexdigest()
if digest != args.expected_hash:
    raise SystemExit("Unexpected payload hash")
record_id = json.loads(payload)["id"]
with sqlite3.connect("earth.sqlite3") as db, db:
    db.execute("PRAGMA synchronous = FULL")
    db.execute("""CREATE TABLE IF NOT EXISTS records (
        id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, payload BLOB NOT NULL
    )""")
    stored = db.execute("SELECT sha256, payload FROM records WHERE id=?", (record_id,)).fetchone()
    if stored is None:
        db.execute("INSERT INTO records VALUES (?, ?, ?)", (record_id, digest, payload))
    elif stored != (digest, payload):
        raise SystemExit("Record ID was reused with different bytes")

receipt_path = None
if not args.suppress_receipt:
    receipt_path = Path(f"receipt-{args.payload.name}.json")
    receipt_path.write_text(json.dumps({"id": record_id, "sha256": digest,
                                        "disposition": "committed"}) + "\n")
print(json.dumps({"id": record_id, "sha256": digest, "duplicate": stored is not None,
                  "receipt": str(receipt_path.resolve()) if receipt_path else None}))
