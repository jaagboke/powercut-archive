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

@app.get("/history.html")
def history_page():
    return FileResponse(STATIC / "history.html")

@app.get("/style.css")
def stylesheet():
    return FileResponse(STATIC / "style.css")

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

@app.get("/api/etr")
def etr_accuracy():
    with db.connect() as conn:
        rows = conn.execute(
            """
            WITH starts AS (
                SELECT dno, min(first_seen) AS capture_start
                FROM outages
                GROUP BY dno
            ),
            etr_changes AS (
                SELECT dno, source_id,
                       count(*) AS revisions,
                       (array_agg(old_value ORDER BY at))[1] AS first_etr
                FROM outage_changes
                WHERE kind = 'updated' AND field = 'etr'
                GROUP BY dno, source_id
            ),
            scored AS (
                SELECT o.dno,
                       o.ended_after + (o.ended_before - o.ended_after) / 2 AS ended_at,
                       o.etr AS final_etr,
                       CASE WHEN c.source_id IS NULL THEN o.etr ELSE c.first_etr::timestamptz END AS first_etr,
                       coalesce(c.revisions, 0) AS revisions
                FROM outages o
                JOIN starts s ON s.dno = o.dno
                LEFT JOIN etr_changes c ON c.dno = o.dno AND c.source_id = o.source_id
                WHERE NOT o.planned
                  AND o.ended_before IS NOT NULL
                  AND o.first_seen > s.capture_start
                  AND o.ended_before - o.ended_after <= interval '30 minutes'
                  AND o.etr IS NOT NULL
            )
            SELECT dno,
                   count(*) AS outages,
                   avg((ended_at < final_etr - interval '30 minutes')::int) AS early,
                   avg((ended_at BETWEEN final_etr - interval '30 minutes'
                                     AND final_etr + interval '30 minutes')::int) AS on_time,
                   avg((ended_at > final_etr + interval '30 minutes')::int) AS late,
                   avg(CASE WHEN first_etr IS NULL THEN NULL
                            ELSE (ended_at BETWEEN first_etr - interval '30 minutes'
                                               AND first_etr + interval '30 minutes')::int END) AS first_on_time,
                   avg(revisions) AS avg_revisions
            FROM scored
            GROUP BY dno
            ORDER BY dno
            """
        ).fetchall()

    def share(value):
        return None if value is None else round(float(value), 3)

    return [
        {
            "dno": dno,
            "outages": count,
            "early": share(early),
            "on_time": share(on_time),
            "late": share(late),
            "first_on_time": share(first_on_time),
            "avg_revisions": round(float(revisions), 1),
        }
        for dno, count, early, on_time, late, first_on_time, revisions in rows
    ]