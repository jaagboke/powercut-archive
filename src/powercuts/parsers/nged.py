import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo

from powercuts.models import Observation

UK = ZoneInfo("Europe/London")

def to_datetime(value: str) -> datetime | None:
    if not value:
        return None
    # NEGD gives no timezone, so we assume UK local time
    return datetime.fromisoformat(value)

def to_int(value: str) -> int | None:
    return int(value) if value else None

def to_float(value: str) -> float | None:
    return float(value) if value else None

def to_postcodes(value: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in value.split(",") if p.strip())

def parse(content: bytes, fetched_at: datetime | None = None) -> list[Observation]:
    text = content.decode("utf-8-sig")
    first_line = text.splitlines()[0]
    dialect = csv.Sniffer().sniff(first_line, delimiters=",\t")

    observations = []
    for row in csv.DictReader(io.StringIO(text), dialect=dialect):
        row = {key: value.strip() for key, value in row.items()}
        observations.append(
            Observation(
                dno="nged",
                source_id=row["fault_id"],
                observed_at=to_datetime(row["upload_date"]),
                status=row["status"],
                planned=row["planned"].upper() == "TRUE",
                category=row["category"] or None,
                voltage=row["voltage"] or None,
                customers_confirmed_off=to_int(row["confirmed_off"]),
                customers_predicted_off=to_int(row["predicted_off"]),
                customers_restored=to_int(row["restored"]),
                reported_at=to_datetime(row["date_of_reported_fault"]),
                etr=to_datetime(row["etr"]),
                restored_at=to_datetime(row["date_of_restoration"]),
                latitude=to_float(row["location_latitude"]),
                longitude=to_float(row["location_longitude"]),
                postcodes=to_postcodes(row["postcode"]),
            )
        )
    return observations