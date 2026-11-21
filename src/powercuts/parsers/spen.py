import json
from datetime import datetime

from powercuts.models import Observation
from powercuts.parsers.common import to_datetime


def parse(content: bytes, fetched_at: datetime | None = None) -> list[Observation]:
    rows = json.loads(content)

    observations = []
    for row in rows:
        sector = row.get("postcode_sector")
        observations.append(
            Observation(
                dno="spen",
                source_id=row["fault_id"],
                observed_at=fetched_at,
                status=row.get("status") or "",
                planned=bool(row.get("planned")),
                category=None,
                voltage=row.get("voltage") or None,
                customers_confirmed_off=None,
                customers_predicted_off=None,
                customers_restored=None,
                reported_at=to_datetime(row.get("date_of_reported_fault")),
                etr=to_datetime(row.get("etr")),
                restored_at=None,
                latitude=None,
                longitude=None,
                postcodes=(sector,) if sector else (),
            )
        )
    return observations