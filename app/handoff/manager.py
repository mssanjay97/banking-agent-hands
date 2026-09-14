import json
from datetime import datetime
from pathlib import Path


HANDOFF_DIR = Path("evidence/handoff")
REQUEST_PATH = HANDOFF_DIR / "intervention_request.json"


def create_handoff_request(
    goal: str,
    step: int,
    reason: str,
    screenshot: str | None = None,
    current_url: str | None = None,
    page_title: str | None = None,
    recovery_hint: str | None = None,
) -> str:
    """
    Record a request for a human to take over the current browser session.
    """

    HANDOFF_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = {
        "status": "WAITING_FOR_HUMAN",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "goal": goal,
        "step": step,
        "reason": reason,
        "screenshot": screenshot,
        "current_url": current_url,
        "page_title": page_title,
        "instructions": (
            "Perform the required manual action in the open browser "
            "session, then signal the automation to resume."
        ),
        "recovery_hint": recovery_hint,
    }

    with REQUEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            request,
            file,
            indent=2,
        )

    return str(REQUEST_PATH)


def mark_handoff_complete() -> None:
    """
    Mark the human intervention as complete.
    """

    if not REQUEST_PATH.exists():
        raise FileNotFoundError(
            "No active handoff request exists."
        )

    with REQUEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        request = json.load(file)

    request["status"] = "HUMAN_COMPLETED"
    request["completed_at"] = (
        datetime.utcnow().isoformat() + "Z"
    )

    with REQUEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            request,
            file,
            indent=2,
        )


def is_handoff_complete() -> bool:
    """
    Check whether the human has completed the intervention.
    """

    if not REQUEST_PATH.exists():
        return False

    with REQUEST_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        request = json.load(file)

    return request.get("status") == "HUMAN_COMPLETED"