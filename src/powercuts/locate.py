import argparse
import json
from dataclasses import replace
from pathlib import Path

import httpx

from powercuts.models import Observation
from powercuts.parsers import spen

LOOKUP_FILE = "sector_locations.json"


def load(data_dir: Path) -> dict:
    path = data_dir / LOOKUP_FILE
    if path.exists():
        return json.loads(path.read_text())
    return {}


def add_locations(observations: list[Observation], lookup: dict) -> list[Observation]:
    located = []
    for obs in observations:
        if obs.latitude is None:
            for sector in obs.postcodes:
                point = lookup.get(sector)
                if point:
                    obs = replace(obs, latitude=point[0], longitude=point[1])
                    break
        located.append(obs)
    return located


def sector_centre(client: httpx.Client, sector: str) -> list[float] | None:
    response = client.get("https://api.postcodes.io/postcodes", params={"q": sector, "limit": 100})
    response.raise_for_status()
    results = [r for r in (response.json().get("result") or []) if r.get("latitude") is not None]
    if not results:
        return None
    lat = sum(r["latitude"] for r in results) / len(results)
    lon = sum(r["longitude"] for r in results) / len(results)
    return [round(lat, 5), round(lon, 5)]


def update(data_dir: Path, client: httpx.Client) -> None:
    lookup = load(data_dir)

    sectors = set()
    for path in (data_dir / "raw" / "spen").rglob("*.json"):
        for obs in spen.parse(path.read_bytes()):
            sectors.update(obs.postcodes)

    new = sorted(sectors - lookup.keys())
    for sector in new:
        try:
            lookup[sector] = sector_centre(client, sector)
        except httpx.HTTPError as e:
            print(f"could not look up {sector}: {e}")

    (data_dir / LOOKUP_FILE).write_text(json.dumps(lookup, indent=1, sort_keys=True))
    print(f"{len(new)} new sectors looked up, {len(lookup)} in total")


def main() -> None:
    parser = argparse.ArgumentParser(description="Look up locations for postcode sectors")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    with httpx.Client(timeout=30) as client:
        update(args.data_dir, client)


if __name__ == "__main__":
    main()