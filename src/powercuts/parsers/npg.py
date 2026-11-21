import json
from datetime import datetime

from powercuts.models import Observation
from powercuts.parsers.common import to_datetime


def parse(content: bytes, fetched_at: datetime | None = None) -> list[Observation]:
    rows = json.loads(content)

    # the same fault can appear on several rows, so merge them by reference
    by_reference = {}
    postcodes = {}
    for row in rows:
        ref = row["reference"]
        by_reference.setdefault(ref, row)
        postcodes.setdefault(ref, [])
        for p in row.get("postcode") or []:
            if p not in postcodes[ref]:
                postcodes[ref].append(p)

    observations = []
    for ref, row in by_reference.items():
        fault_type = row.get("type") or ""
        nature = row.get("natureofoutage") or ""
        observations.append(
            Observation(
                dno="npg",
                source_id=ref,
                observed_at=fetched_at,
                status=str(row.get("incidentstatus") or ""),
                planned=ref.startswith("PPC") or "planned" in nature.lower(),
                category=nature or None,
                voltage=fault_type[:2] if fault_type[:2] in ("LV", "HV") else None,
                customers_confirmed_off=row.get("totalconfirmedpowercut"),
                customers_predicted_off=row.get("totalpredictedpowercut"),
                customers_restored=None,
                reported_at=to_datetime(row.get("loggedtime")),
                etr=to_datetime(row.get("estimatedtimetillresolution")),
                restored_at=None,
                latitude=row.get("lat"),
                longitude=row.get("lng"),
                postcodes=tuple(postcodes[ref]),
            )
        )
    return observations