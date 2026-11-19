# Feed survey

## NGED (checked 17 Nov 2026)

- Format: CSV, no API key
- Incident ID: `fault_id` (e.g. INCD-116674-l), need to confirm it's stable across polls
- Customer counts: `confirmed_off`, `predicted_off`, `restored` (partial restorations visible)
- Times: `date_of_reported_fault`, `last_updated`, `etr`, `date_of_restoration`, `date_of_completion`
- `etr` can be blank
- Asset info: `category` (e.g. LV UNDERGROUND), `voltage`
- Location: `location_latitude`, `location_longitude`, plus `postcode` (comma-separated list in one field)
- Planned work: `planned` flag + `planned_outage_*` fields
- `upload_date` changes every NGED refresh, so file hash changes even if no outage did
- `resource_status` codes: LEFS = ?, ONS = ?

## Still to find out (after a few days of capture)
- How often does NGED refresh (`upload_date` interval)?
- Does `fault_id` stay the same for the life of an outage?
- When an outage is restored, does it stay in the feed with a restoration date, or disappear?