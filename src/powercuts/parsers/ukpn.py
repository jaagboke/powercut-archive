import json
from datetime import datetime

from powercuts.models import Observation
from powercuts.parsers.common import UK, to_datetime


def tidy_postcode(value: str) -> str:
    value = value.replace(" ", "").upper()
    return f"{value[:-3]} {value[-3:]}"


def parse(content: bytes, fetched_at: datetime | None = None) -> list[Observation]:
    rows = json.loads(content)

    observations = []
    for row in rows:
        point = row.get("geopoint") or {}
        full_postcodes = row.get("fullpostcodedata") or ""
        observations.append(
            Observation(
                dno="ukpn",
                source_id=row["incidentreference"],
                observed_at=fetched_at,
                status=str(row.get("statusid") or ""),
                planned=row.get("powercuttype") == "Planned",
                category=row.get("incidentcategory") or None,
                voltage=None,
                customers_confirmed_off=row.get("nocustomeraffected"),
                customers_predicted_off=None,
                customers_restored=None,
                # UKPN times have no timezone, so assume UK local time
                reported_at=to_datetime(row.get("receiveddate"), UK),
                etr=to_datetime(row.get("estimatedrestorationdate"), UK),
                restored_at=to_datetime(row.get("restoreddatetime"), UK),
                latitude=point.get("lat"),
                longitude=point.get("lon"),
                postcodes=tuple(tidy_postcode(p) for p in full_postcodes.split(";") if p.strip()),
            )
        )
    return observations