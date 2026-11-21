from datetime import UTC, datetime
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")


def to_datetime(value: str | None, default_tz=UTC) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt