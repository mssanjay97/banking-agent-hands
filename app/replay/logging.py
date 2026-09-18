import json
from datetime import datetime
from pathlib import Path


LOG_FILE = Path("evidence/replay/replay.jsonl")


def _redact_action(
    action: dict,
) -> dict:
    """
    Remove concrete runtime input values
    before persisting replay logs.
    """
    redacted = action.copy()

    if "value" in redacted:
        redacted["value"] = "<redacted>"

    return redacted

def log_event(
    event_type: str,
    data: dict,
):
    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_data = data.copy()

    if "action" in safe_data:
        safe_data["action"] = _redact_action(
            safe_data["action"]
        )

    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "data": safe_data,
    }

    with LOG_FILE.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(record)
            + "\n"
        )