"""Preview explicit bad sample IDs; --apply requires a new SQLite backup path."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def clean(database, ids, backup=None):
    ids = sorted(set(ids))
    if not ids or any(i < 1 for i in ids):
        raise ValueError("Provide positive air_readings IDs")
    database = Path(database).resolve(strict=True)
    placeholders = ",".join("?" for _ in ids)
    mode = "rw" if backup is not None else "ro"
    with closing(sqlite3.connect(database.as_uri() + "?mode=" + mode)) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            f"SELECT * FROM air_readings WHERE id IN ({placeholders}) ORDER BY id", ids
        ).fetchall()
        if len(rows) != len(ids):
            raise ValueError("Some IDs do not exist; no readings removed")
        print(json.dumps([dict(row) for row in rows], indent=2))
        if backup is None:
            print(f"Preview only: {len(rows)} readings; database unchanged")
            return

        backup = Path(backup).resolve()
        # Never overwrite a previous backup (or the source database).
        with backup.open("xb"):
            pass
        with closing(sqlite3.connect(backup)) as destination:
            con.backup(destination)
        with con:
            con.execute(f"DELETE FROM air_readings WHERE id IN ({placeholders})", ids)
        print(f"Removed {len(rows)} readings. Full database backup: {backup}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--ids", required=True, nargs="+", type=int)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    if args.apply and args.backup is None:
        parser.error("--apply requires --backup pointing to a new file")
    if args.backup is not None and not args.apply:
        parser.error("--backup requires --apply")
    clean(args.database, args.ids, args.backup)


if __name__ == "__main__":
    main()
