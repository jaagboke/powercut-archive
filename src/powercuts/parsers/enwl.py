import json
from datetime import datetime

from powercuts.models import Observation
from powercuts.parsers.common import to_datetime


def parse(content: bytes, fetched_at: datetime | None = None) -> list[Observation]:
    rows = json.loads(content)

    observations = []
    for row in rows:
        point = row.get("geo_point_2d") or {}
        incident_type = row.get("incident_type") or ""
        observations.append(
            Observation(
                dno="enwl",
                source_id=row["incident_num"],
                observed_at=fetched_at,
                status=row.get("incident_status") or "",
                planned="planned" in incident_type.lower(),
                category=incident_type or None,
                voltage=None,
                customers_confirmed_off=row.get("customers_off_supply"),
                customers_predicted_off=None,
                customers_restored=None,
                reported_at=to_datetime(row.get("outage_time")),
                etr=to_datetime(row.get("estimated_restoration_time")),
                restored_at=None,
                latitude=point.get("lat"),
                longitude=point.get("lon"),
                postcodes=(),
            )
        )
    return observations