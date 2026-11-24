# powercut-archive

Every DNO in Great Britain publishes a live feed of current power cuts. None of them keep it. Once a fault is restored it drops off the feed, and that's the end of the public record.

This project polls all six DNO groups every five minutes, keeps every response, and rebuilds them into one history: a row per outage, when it was first seen, how its ETR and customer numbers changed, and when it ended.

How long do outages actually last? How good are the restoration estimates? How do the DNOs compare on the same measures?

## What's covered

| DNO | Format | Key needed |
|---|---|---|
| National Grid Electricity Distribution | CSV | No |
| SSEN Distribution | JSON (Power Track API) | No |
| Northern Powergrid | JSON (Opendatasoft) | No |
| SP Energy Networks | JSON (Opendatasoft) | Yes |
| UK Power Networks | JSON (Opendatasoft) | No |
| Electricity North West | JSON (Opendatasoft) | Yes |

## How it works

```
DNO feeds -> capture -> archive/raw -> parser -> tracker -> Postgres -> web
```

**Capture.** A GitHub Actions job polls each feed and saves the raw response, but only when it has changed. Every poll, successful or not, goes in `archive/poll_log.jsonl`. GitHub's own scheduler turned out to be unreliable (runs were landing every 8 to 12 hours), so the job is triggered every five minutes from an external cron service instead.

**Parsers.** One per DNO. Each turns that DNO's format into a common `Observation`, so nothing downstream needs to know where the data came from.

**Tracker.** Works through the snapshots in order and follows each fault through its life: appeared, updated (status, ETR, customer counts), ended, and occasionally reopened. A fault that disappears from the feed is treated as ended, but the end time is stored as a window between the last snapshot it was in and the first one it wasn't. If capture misses a few hours, the window is a few hours wide, and the history views leave those outages out rather than guess. An empty feed is treated as broken, not as "no power cuts anywhere".

**Processor.** Rebuilds the database from the raw snapshots every five minutes. The raw files are the source of truth, so any change to a parser or the tracker can be replayed over the whole history.

**Web.** FastAPI serving a live map (MapLibre) and a history page (Chart.js) with outages per day, how long they last, and how accurate the ETRs were.

## Running it locally

You'll need Docker and Python 3.11+.

```
git clone https://github.com/jaagboke/powercut-archive.git
cd powercut-archive
docker compose up -d --build
```

Then open http://localhost:8000. The live map is at `/`, history at `/history`.

New snapshots arrive in the repo from GitHub Actions, so `git pull` to bring your copy up to date. The processor picks them up within five minutes.

To poll a feed by hand:

```
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m powercuts --dno nged --once --data-dir /tmp/test
```

SPEN and ENWL need API keys from their open data portals, set as `SPEN_API_KEY` and `ENWL_API_KEY`.

## Limitations

- It only knows what the DNOs publish. Anything that doesn't make their live maps isn't here.
- End times are only as precise as the polling interval, five minutes at best.
- Some status fields (UKPN, Northern Powergrid) are stored as raw codes because I haven't confirmed what they mean.
- The processor rebuilds everything on each run. Fine for now, but it will need to become incremental as the archive grows.
- Durations start from the DNO's reported time where one is given, otherwise from when the fault was first seen.

## Data

The data belongs to the DNOs and is published under their own open data licences. Check those before reusing anything from `archive/`.
