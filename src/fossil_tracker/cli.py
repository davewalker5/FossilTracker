"""Command-line helpers for Fossil Tracker."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .config import database_path
from .db import apply_migrations, seed_specimens, specimen_count


def main(argv: list[str] | None = None) -> int:
    """Run the Fossil Tracker command-line interface.

    :param argv: Optional argument list; uses process arguments when omitted.
    :return: Process-style exit code.
    """

    parser = argparse.ArgumentParser(prog="fossil-tracker")
    parser.add_argument(
        "--db",
        type=Path,
        default=database_path(),
        help="SQLite database path. Defaults to data/fossil_tracker.sqlite3.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Apply all outstanding schema migrations.")
    subparsers.add_parser("seed", help="Add the suggested starter specimens if empty.")
    subparsers.add_parser("count", help="Print the number of specimens.")

    datasette_parser = subparsers.add_parser("datasette", help="Open the database in Datasette.")
    datasette_parser.add_argument("--port", type=int, default=8001)

    args = parser.parse_args(argv)

    if args.command == "init-db":
        apply_migrations(args.db)
        print(f"Database ready: {args.db}")
        return 0

    if args.command == "seed":
        apply_migrations(args.db)
        added = seed_specimens(args.db)
        print(f"Added {added} starter specimen{'s' if added != 1 else ''}.")
        return 0

    if args.command == "count":
        apply_migrations(args.db)
        print(specimen_count(args.db))
        return 0

    if args.command == "datasette":
        apply_migrations(args.db)
        return subprocess.call(
            [sys.executable, "-m", "datasette", str(args.db), "--port", str(args.port)]
        )

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
