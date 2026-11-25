#!/usr/bin/env python3
"""Commit the known smoke-test payload before creating the return receipt."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("expected_id")
parser.add_argument("expected_hash")
args = parser.parse_args()

payload = Path("testfile1").read_bytes()
digest = hashlib.sha256(payload).hexdigest()
record_id = json.loads(payload)["id"]
if (record_id, digest) != (args.expected_id, args.expected_hash):
    raise SystemExit("Earth payload does not match the expected ID and SHA-256")

with sqlite3.connect("earth.sqlite3") as db, db:
    db.execute("PRAGMA synchronous = FULL")
    db.execute("""CREATE TABLE records (
        id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, payload BLOB NOT NULL
    )""")
    db.execute("INSERT INTO records VALUES (?, ?, ?)", (record_id, digest, payload))

with sqlite3.connect("earth.sqlite3") as db:
    persisted = db.execute("SELECT id, sha256, payload FROM records").fetchall()
    if persisted != [(record_id, digest, payload)]:
        raise SystemExit("Earth commit verification failed")

receipt = {"id": record_id, "sha256": digest, "disposition": "committed"}
Path("receipt.json").write_text(json.dumps(receipt, sort_keys=True) + "\n")
print(f"Earth committed {record_id}, {len(payload)} bytes, SHA-256 {digest}")
