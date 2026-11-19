import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from powercuts.sources import FEEDS


def read_last_hash(dno_dir: Path) -> str | None:
    hash_file = dno_dir / "last_hash"
    if hash_file.exists():
        return hash_file.read_text().strip()
    return None


def write_log(data_dir: Path, record: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / "poll_log.jsonl", "a") as f:
        f.write(json.dumps(record) + "\n")


def capture(dno: str, client: httpx.Client, data_dir: Path, now: datetime | None = None) -> dict:
    feed = FEEDS[dno]
    now = now or datetime.now(UTC)
    record = {"dno": dno, "fetched_at": now.isoformat(), "ok": False}

    try:
        response = client.get(feed["url"])
        response.raise_for_status()
    except httpx.HTTPError as e:
        record["error"] = f"{type(e).__name__}: {e}"
        write_log(data_dir, record)
        return record

    content = response.content
    digest = hashlib.sha256(content).hexdigest()
    dno_dir = data_dir / "raw" / dno
    changed = digest != read_last_hash(dno_dir)

    record["ok"] = True
    record["status_code"] = response.status_code
    record["bytes"] = len(content)
    record["sha256"] = digest
    record["changed"] = changed

    if changed:
        day_dir = dno_dir / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        path = day_dir / f"{now.strftime('%H%M%SZ')}.{feed['extension']}"
        path.write_bytes(content)
        (dno_dir / "last_hash").write_text(digest)
        record["saved_to"] = str(path.relative_to(data_dir))

    write_log(data_dir, record)
    return record