from dataclasses import dataclass
from datetime import datetime

from powercuts.models import Observation

TRACKED_FIELDS = [
    "status",
    "etr",
    "customers_confirmed_off",
    "customers_predicted_off",
    "customers_restored",
    "restored_at",
]


@dataclass
class Outage:
    dno: str
    source_id: str
    first_seen: datetime
    last_seen: datetime
    latest: Observation
    ended_after: datetime | None = None
    ended_before: datetime | None = None

    @property
    def is_open(self) -> bool:
        return self.ended_before is None


@dataclass(frozen=True)
class Change:
    dno: str
    source_id: str
    at: datetime
    kind: str  # appeared, updated, ended, reopened
    field: str | None = None
    old: object = None
    new: object = None


class Tracker:
    def __init__(self, dno: str):
        self.dno = dno
        self.outages: dict[str, Outage] = {}
        self.last_snapshot_time: datetime | None = None

    def apply(self, observations: list[Observation]) -> list[Change]:
        # an empty feed is far more likely to be broken than to mean no faults anywhere
        if not observations:
            return []

        snapshot_time = max(o.observed_at for o in observations)
        if self.last_snapshot_time and snapshot_time <= self.last_snapshot_time:
            return []

        changes = []
        seen = set()

        for obs in observations:
            seen.add(obs.source_id)
            outage = self.outages.get(obs.source_id)

            if outage is None:
                self.outages[obs.source_id] = Outage(
                    dno=self.dno,
                    source_id=obs.source_id,
                    first_seen=snapshot_time,
                    last_seen=snapshot_time,
                    latest=obs,
                )
                changes.append(Change(self.dno, obs.source_id, snapshot_time, "appeared"))
                continue

            if not outage.is_open:
                outage.ended_after = None
                outage.ended_before = None
                changes.append(Change(self.dno, obs.source_id, snapshot_time, "reopened"))

            for field in TRACKED_FIELDS:
                old = getattr(outage.latest, field)
                new = getattr(obs, field)
                if old != new:
                    changes.append(Change(self.dno, obs.source_id, snapshot_time, "updated", field, old, new))

            outage.latest = obs
            outage.last_seen = snapshot_time

        for outage in self.outages.values():
            if outage.is_open and outage.source_id not in seen:
                outage.ended_after = outage.last_seen
                outage.ended_before = snapshot_time
                changes.append(Change(self.dno, outage.source_id, snapshot_time, "ended"))

        self.last_snapshot_time = snapshot_time
        return changes