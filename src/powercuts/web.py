from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from powercuts import db

app = FastAPI()
STATIC = Path(__file__).parent / "static"


def iso(value):
    return value.isoformat() if value else None


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/open")
def open_outages():
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT dno, source_id, status, planned, category, customers_confirmed_off,
                   first_seen, etr, latitude, longitude
            FROM outages
            WHERE ended_before IS NULL AND latitude IS NOT NULL
            """
        ).fetchall()

    features = []
    for dno, source_id, status, planned, category, customers, first_seen, etr, lat, lon in rows:
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "dno": dno,
                    "source_id": source_id,
                    "status": status,
                    "planned": planned,
                    "category": category,
                    "customers": customers,
                    "first_seen": iso(first_seen),
                    "etr": iso(etr),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/summary")
def summary():
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT dno,
                   count(*) FILTER (WHERE ended_before IS NULL) AS open_now,
                   count(*) FILTER (WHERE ended_before > now() - interval '24 hours') AS ended_24h,
                   coalesce(sum(customers_confirmed_off) FILTER (WHERE ended_before IS NULL), 0) AS customers_off
            FROM outages
            GROUP BY dno
            ORDER BY dno
            """
        ).fetchall()
        updated = conn.execute("SELECT max(last_seen) FROM outages").fetchone()[0]

    return {
        "updated": iso(updated),
        "dnos": [
            {"dno": dno, "open_now": open_now, "ended_24h": ended, "customers_off": customers}
            for dno, open_now, ended, customers in rows
        ],
    }