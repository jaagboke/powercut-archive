import csv
import io
import sys
from collections import Counter
from pathlib import Path


def read_snapshot(path):
    text = path.read_text(encoding="utf-8-sig")
    first_line = text.splitlines()[0]
    dialect = csv.Sniffer().sniff(first_line, delimiters=",\t")
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def main(folder):
    files = sorted(Path(folder).rglob("*.csv"))
    print(f"{len(files)} snapshots\n")

    previous = {}
    last_status_when_gone = Counter()

    for path in files:
        rows = read_snapshot(path)
        faults = {row["fault_id"]: row for row in rows}

        if len(faults) != len(rows):
            print(f"  warning: {path.name} has {len(rows) - len(faults)} duplicate fault_ids")

        upload = rows[0]["upload_date"] if rows else "?"
        new = faults.keys() - previous.keys()
        gone = previous.keys() - faults.keys()
        still_there = faults.keys() & previous.keys()
        etr_changed = sum(1 for f in still_there if faults[f]["etr"] != previous[f]["etr"])

        for fault_id in gone:
            last_status_when_gone[previous[fault_id]["status"]] += 1

        print(
            f"{path.parent.name}/{path.name}  upload={upload}  faults={len(faults)}"
            f"  new={len(new)}  gone={len(gone)}  etr_changed={etr_changed}"
        )
        previous = faults

    print("\nLast status of faults before they disappeared:")
    for status, count in last_status_when_gone.most_common():
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/raw/nged")