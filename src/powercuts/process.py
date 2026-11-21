import argparse
import time
from datetime import UTC, datetime
from pathlib import Path

from powercuts import db
from powercuts.parsers import nged, ssen
from powercuts.sources import FEEDS
from powercuts.tracker import Tracker

PARSERS = {
    "nged": nged.parse,
    "ssen": ssen.parse,
}


def rebuild(dno: str, data_dir: Path) -> None:
    parse = PARSERS[dno]
    extension = FEEDS[dno]["extension"]
    files = sorted((data_dir / "raw" / dno).rglob(f"*.{extension}"))

    tracker = Tracker(dno)
    changes = []
    for path in files:
        changes += tracker.apply(parse(path.read_bytes()))

    with db.connect() as conn:
        db.create_tables(conn)
        db.clear_dno(conn, dno)
        db.save_outages(conn, tracker.outages.values())
        db.save_changes(conn, changes)

    now = datetime.now(UTC).isoformat(timespec="seconds")
    print(f"{now} {dno}: {len(files)} snapshots -> {len(tracker.outages)} outages, {len(changes)} changes", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild outage tables from raw snapshots")
    parser.add_argument("--dno", choices=PARSERS.keys(), help="one DNO, or leave out for all", required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--interval", type=int, default=0, help="seconds between runs, 0 = run once")
    args = parser.parse_args()

    dnos = [args.dno] if args.dno else list(PARSERS)

    while True:
        for dno in dnos:
            rebuild(dno, args.data_dir)
        if not args.interval:
            break
        time.sleep(args.interval)

    while True:
        rebuild(args.dno, args.data_dir)
        if not args.interval:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()