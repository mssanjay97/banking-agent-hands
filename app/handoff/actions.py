import json
from datetime import datetime
from pathlib import Path


HANDOFF_DIR = Path("evidence/handoff")
ACTIONS_PATH = HANDOFF_DIR / "human_actions.jsonl"


def record_human_action(
    action: str,
    description: str,
):
    """
    Record a manual action performed by the human operator.

    Do not store secrets or sensitive values here.
    """

    HANDOFF_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "actor": "human_operator",
        "action": action,
        "description": description,
    }

    with ACTIONS_PATH.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(event) + "\n"
        )