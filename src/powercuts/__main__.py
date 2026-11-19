import argparse
import time
from pathlib import Path

import httpx

from powercuts.capture import capture
from powercuts.sources import FEEDS

USER_AGENT = "powercut-archive/0.1 (personal research project)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Save raw snapshots of DNO power cut feeds")
    parser.add_argument("--dno", choices=FEEDS.keys(), required=True)
    parser.add_argument("--interval", type=int, default=300, help="seconds between polls")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--once", action="store_true", help="poll once and exit")
    args = parser.parse_args()

    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        while True:
            record = capture(args.dno, client, args.data_dir)
            if record["ok"]:
                status = "saved" if record["changed"] else "unchanged"
                print(f"{record['fetched_at']} {args.dno} {status} ({record['bytes']} bytes)", flush=True)
            else:
                print(f"{record['fetched_at']} {args.dno} FAILED {record['error']}", flush=True)

            if args.once:
                break
            time.sleep(args.interval)


if __name__ == "__main__":
    main()