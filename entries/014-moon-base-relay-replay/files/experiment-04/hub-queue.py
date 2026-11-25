#!/usr/bin/env python3
"""Small SQLite spool used by the contact-gated bench controller."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("enqueue", "claim", "ack", "retry", "status"))
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()
    with sqlite3.connect("hub.sqlite3") as db, db:
        db.execute("PRAGMA synchronous=FULL")
        db.execute("""CREATE TABLE IF NOT EXISTS queue (
            id TEXT PRIMARY KEY, payload BLOB NOT NULL, sha256 TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0
        )""")
        if args.action == "enqueue":
            data = (args.value + "\n").encode()
            db.execute("INSERT INTO queue (id,payload,sha256) VALUES (?,?,?)",
                       (json.loads(data)["id"], data, hashlib.sha256(data).hexdigest()))
        elif args.action == "claim":
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM queue WHERE state='inflight'").fetchone()[0]:
                raise SystemExit("One record is already awaiting an Earth receipt")
            record = db.execute(
                "SELECT id,payload FROM queue WHERE state='queued' ORDER BY rowid LIMIT 1"
            ).fetchone()
            if record is None:
                raise SystemExit("Queue empty")
            record_id, data = record
            path = Path(f"queue-{record_id}.json").resolve()
            path.write_bytes(data)
            db.execute("UPDATE queue SET state='inflight', attempts=attempts+1 WHERE id=?",
                       (record_id,))
            print(json.dumps({"id": record_id, "path": str(path)}))
        elif args.action == "retry":
            result = db.execute("UPDATE queue SET state='queued' WHERE id=? AND state='inflight'",
                                (args.value,))
            if result.rowcount != 1:
                raise SystemExit("Retry requires one inflight record")
        elif args.action == "ack":
            receipt = json.loads(args.value)
            result = db.execute(
                "UPDATE queue SET state='acked' WHERE id=? AND sha256=? AND state='inflight'",
                (receipt["id"], receipt["sha256"]),
            )
            if receipt["disposition"] != "committed" or result.rowcount != 1:
                raise SystemExit("Unexpected Earth receipt")
        else:
            print(json.dumps(db.execute("SELECT id,state,attempts FROM queue ORDER BY rowid").fetchall()))


if __name__ == "__main__":
    main()
