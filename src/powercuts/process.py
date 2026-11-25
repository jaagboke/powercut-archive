import argparse
import time
from datetime import UTC, datetime
from pathlib import Path

from powercuts import db, locate
from powercuts.parsers import enwl, nged, npg, spen, ssen, ukpn
from powercuts.sources import FEEDS
from powercuts.tracker import Tracker

PARSERS = {
    "nged": nged.parse,
    "ssen": ssen.parse,
    "npg": npg.parse,
    "spen": spen.parse,
    "ukpn": ukpn.parse,
    "enwl": enwl.parse,
}


def fetched_time(path: Path) -> datetime:
    # snapshots are saved as raw/<dno>/<YYYY-MM-DD>/<HHMMSS>Z.<ext>
    return datetime.strptime(f"{path.parent.name} {path.stem}", "%Y-%m-%d %H%M%SZ").replace(tzinfo=UTC)


def rebuild(dno: str, data_dir: Path) -> None:
    parse = PARSERS[dno]
    extension = FEEDS[dno]["extension"]
    files = sorted((data_dir / "raw" / dno).rglob(f"*.{extension}"))

    lookup = locate.load(data_dir)
    tracker = Tracker(dno)
    changes = []
    for path in files:
        observations = parse(path.read_bytes(), fetched_time(path))
        observations = locate.add_locations(observations, lookup)
        changes += tracker.apply(observations)

    with db.connect() as conn:
        db.create_tables(conn)
        db.clear_dno(conn, dno)
        db.save_outages(conn, tracker.outages.values())
        db.save_changes(conn, changes)

    now = datetime.now(UTC).isoformat(timespec="seconds")
    print(
        f"{now} {dno}: {len(files)} snapshots -> {len(tracker.outages)} outages, {len(changes)} changes",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild outage tables from raw snapshots")
    parser.add_argument("--dno", choices=PARSERS.keys(), help="one DNO, or leave out for all")
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


if __name__ == "__main__":
    main()