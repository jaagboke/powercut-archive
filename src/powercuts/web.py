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

@app.get("/history")
def history_page():
    return FileResponse(STATIC / "history.html")


@app.get("/api/daily")
def daily():
    with db.connect() as conn:
        rows = conn.execute(
            """
            WITH starts AS (
                SELECT dno, min(first_seen) AS capture_start
                FROM outages
                GROUP BY dno
            )
            SELECT o.dno,
                   (o.first_seen AT TIME ZONE 'Europe/London')::date AS day,
                   count(*) AS outages
            FROM outages o
            JOIN starts s ON s.dno = o.dno
            WHERE NOT o.planned
              AND o.first_seen > s.capture_start
            GROUP BY o.dno, day
            ORDER BY day, o.dno
            """
        ).fetchall()

    return [{"dno": dno, "day": day.isoformat(), "outages": count} for dno, day, count in rows]

@app.get("/api/durations")
def durations():
    with db.connect() as conn:
        rows = conn.execute(
            """
            WITH starts AS (
                SELECT dno, min(first_seen) AS capture_start
                FROM outages
                GROUP BY dno
            ),
            durations AS (
                SELECT o.dno,
                       o.ended_after + (o.ended_before - o.ended_after) / 2
                           - coalesce(o.reported_at, o.first_seen) AS duration
                FROM outages o
                JOIN starts s ON s.dno = o.dno
                WHERE NOT o.planned
                  AND o.ended_before IS NOT NULL
                  AND o.first_seen > s.capture_start
                  AND o.ended_before - o.ended_after <= interval '30 minutes'
            )
            SELECT dno,
                   count(*) AS outages,
                   extract(epoch FROM percentile_cont(0.5) WITHIN GROUP (ORDER BY duration)) / 60 AS median_minutes,
                   extract(epoch FROM percentile_cont(0.9) WITHIN GROUP (ORDER BY duration)) / 60 AS p90_minutes,
                   avg((duration > interval '12 hours')::int) AS share_over_12h
            FROM durations
            WHERE duration > interval '0'
            GROUP BY dno
            ORDER BY dno
            """
        ).fetchall()

    return [
        {
            "dno": dno,
            "outages": count,
            "median_minutes": round(median),
            "p90_minutes": round(p90),
            "share_over_12h": round(float(share), 3),
        }
        for dno, count, median, p90, share in rows
    ]