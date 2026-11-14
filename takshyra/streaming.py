"""Small deterministic telemetry stream lab; no broker or customer data."""

from datetime import datetime, timedelta, timezone

SCENARIOS = {"CLEAN", "SCHEMA_V15", "SINK_GAP", "CONSUMER_LAG", "DUPLICATE", "LATE_EVENT"}
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def evaluate(scenario: str) -> tuple[str, str | None, dict[str, int]]:
    if scenario not in SCENARIOS:
        raise ValueError("Unknown stream scenario")
    events = [
        {"id": index, "schema": 14, "event_time": BASE + timedelta(seconds=index * 10),
         "ingest_time": BASE + timedelta(seconds=index * 10 + 2)}
        for index in range(4)
    ]
    if scenario == "SCHEMA_V15":
        events[3]["schema"] = 15
    elif scenario == "CONSUMER_LAG":
        events[3]["ingest_time"] += timedelta(seconds=120)
    elif scenario == "LATE_EVENT":
        events[3]["event_time"] -= timedelta(seconds=100)
    elif scenario == "DUPLICATE":
        events.append(dict(events[1]))

    seen: set[int] = set()
    decoded: list[dict] = []
    duplicates = dlq = 0
    for event in events:
        if event["id"] in seen:
            duplicates += 1
            continue
        seen.add(event["id"])
        if event["schema"] != 14:
            dlq += 1
            continue
        decoded.append(event)
    written = len(decoded) - int(scenario == "SINK_GAP")
    watermark = max(event["event_time"] for event in events) - timedelta(seconds=30)
    late = sum(event["event_time"] < watermark for event in decoded)
    lag = max(int((event["ingest_time"] - event["event_time"]).total_seconds()) for event in events)
    metrics = {
        "source_events": len(events), "unique_events": len(seen), "decoded": len(decoded),
        "written": written, "dlq": dlq, "duplicates": duplicates, "late": late,
        "max_lag_seconds": lag, "source_sink_gap": len(seen) - written,
    }
    failures = {
        "SCHEMA_V15": "STREAM_SCHEMA_INCOMPATIBLE",
        "SINK_GAP": "STREAM_RECONCILIATION_GAP",
        "CONSUMER_LAG": "STREAM_CONSUMER_LAG",
        "LATE_EVENT": "STREAM_LATE_EVENT",
    }
    code = failures.get(scenario)
    return ("FAIL" if code else "PASS", code, metrics)
