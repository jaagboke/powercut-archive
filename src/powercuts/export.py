import json
from pathlib import Path

from powercuts import web


def save(out: Path, name: str, data) -> None:
    (out / f"{name}.json").write_text(json.dumps(data))
    print(f"wrote {name}.json")


def main() -> None:
    out = Path("site/api")
    out.mkdir(parents=True, exist_ok=True)

    save(out, "open", web.open_outages())
    save(out, "summary", web.summary())

    for period_name, days in web.PERIODS.items():
        save(out, f"period_{period_name}", web.period(days))

    for range_name, days in web.RANGES.items():
        save(out, f"daily_{range_name}", web.daily(days))
        save(out, f"durations_{range_name}", web.durations(days))
        save(out, f"etr_{range_name}", web.etr_accuracy(days))


if __name__ == "__main__":
    main()