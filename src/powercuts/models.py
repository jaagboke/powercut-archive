from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Observation:
    """One fault as it appeared in one snapshot."""

    dno:str
    source_id: str
    observed_at: datetime
    status: str
    planned: bool
    category: str | None
    voltage: str | None
    customers_confirmed_off: int|None
    customers_predicted_off: int | None
    customers_restored: int|None
    reported_at: datetime | None
    etr: datetime | None
    restored_at: datetime | None
    latitude: float| None
    longitude: float| None
    postcodes: tuple[str, ...]