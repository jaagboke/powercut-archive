import json
from pathlib import Path
from powercuts import  web

ENSPOINTS = {
    "open": web.open_outages,
    "summary": web.summary,
    "daily": web.daily,
    "durations": web.durations,
    "etr": web.etr_accuracy
}

def main() -> None:
    out = Path("site/api")
    out.mkdir(parents=True, exist_ok=True)
    for name, endpoint in ENSPOINTS.items():
        (out / f"{name}.json").write_text(json.dumps(endpoint()))
        print(f"wrote {name}.json")

if __name__ == "__main__":
    main()