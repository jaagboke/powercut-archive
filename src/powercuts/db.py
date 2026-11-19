import os

import psycopg

DEFAULT_URL = "postgresql://powercuts:powercuts@localhost:5432/powercuts"

SCHEMA = """
CREATE TABLE IF NOT EXISTS outages (
    dno text NOT NULL,
    source_id text NOT NULL,
    first_seen timestamptz NOT NULL,
    last_seen timestamptz NOT NULL,
    ended_after timestamptz,
    ended_before timestamptz,
    status text,
    planned boolean,
    category text,
    voltage text,
    customers_confirmed_off integer,
    customers_predicted_off integer,
    customers_restored integer,
    reported_at timestamptz,
    etr timestamptz,
    restored_at timestamptz,
    latitude double precision,
    longitude double precision,
    postcodes text[],
    PRIMARY KEY (dno, source_id)
);

CREATE TABLE IF NOT EXISTS outage_changes (
    id bigserial PRIMARY KEY,
    dno text NOT NULL,
    source_id text NOT NULL,
    at timestamptz NOT NULL,
    kind text NOT NULL,
    field text,
    old_value text,
    new_value text,
    FOREIGN KEY (dno, source_id) REFERENCES outages (dno, source_id)
);
"""


def connect():
    return psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_URL))


def create_tables(conn):
    conn.execute(SCHEMA)


def clear_dno(conn, dno):
    conn.execute("DELETE FROM outage_changes WHERE dno = %s", (dno,))
    conn.execute("DELETE FROM outages WHERE dno = %s", (dno,))


def save_outages(conn, outages):
    rows = []
    for o in outages:
        obs = o.latest
        rows.append(
            (
                o.dno,
                o.source_id,
                o.first_seen,
                o.last_seen,
                o.ended_after,
                o.ended_before,
                obs.status,
                obs.planned,
                obs.category,
                obs.voltage,
                obs.customers_confirmed_off,
                obs.customers_predicted_off,
                obs.customers_restored,
                obs.reported_at,
                obs.etr,
                obs.restored_at,
                obs.latitude,
                obs.longitude,
                list(obs.postcodes),
            )
        )

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO outages (
                dno, source_id, first_seen, last_seen, ended_after, ended_before,
                status, planned, category, voltage,
                customers_confirmed_off, customers_predicted_off, customers_restored,
                reported_at, etr, restored_at,
                latitude, longitude, postcodes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )


def to_text(value):
    return None if value is None else str(value)


def save_changes(conn, changes):
    rows = [(c.dno, c.source_id, c.at, c.kind, c.field, to_text(c.old), to_text(c.new)) for c in changes]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO outage_changes (dno, source_id, at, kind, field, old_value, new_value)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            rows,
        )