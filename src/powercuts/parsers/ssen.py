import json
from datetime import datetime
from powercuts.models import Observation

def to_datetime(value: str) -> datetime | None:
    if not value:
        return  None
    return datetime.fromisoformat(value)

def parse(content: bytes, fetched_at: datetime | None = None) -> list[Observation]:
    data = json.loads(content)
    observed_at = to_datetime(data["timestampUtc"])
    observations = []
    for fault in data["faults"]:
        fault_type = fault.get("type") or None
        location = fault.get("location")  or {}
        observations.append(
            Observation(
                dno="ssen",
                source_id=fault["reference"],
                observed_at=observed_at,
                status=fault.get("jobStatus") or "",
                planned=fault_type == "PSI",
                category=fault_type,
                voltage=fault_type if fault_type in ("LV", "HV") else None,
                customers_confirmed_off=fault.get("customerCount"),
                customers_predicted_off=None,
                customers_restored=None,
                reported_at=to_datetime(fault.get("loggedAtUtc")),
                etr=to_datetime(fault.get("estimatedRestorationTimeUtc")),
                restored_at=None,
                latitude=location.get("latitude"),
                longitude=location.get("longitude"),
                postcodes=tuple(fault.get("affectedAreas") or []),
            )
        )
    return observations