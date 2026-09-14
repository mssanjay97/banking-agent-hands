from pathlib import Path
import json


DISCOVERY_DIR = Path("evidence/discovery")


class DiscoveryRecorder:
    def __init__(self, start_url: str):
        self.start_url = start_url
        self.actions = []

    def record(self, action: dict):
        recorded_action = action.copy()

        # Never persist the concrete input value.
        # Convert discovered values into reusable parameters.
        if recorded_action.get("action") == "fill":
            recorded_action["value"] = "{{member_id}}"

        self.actions.append(recorded_action)

    def save(
        self,
        filename: str = "discovery_actions.json",
    ):
        DISCOVERY_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = DISCOVERY_DIR / filename

        artifact = {
            "start_url": self.start_url,
            "actions": self.actions,
        }

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                artifact,
                file,
                indent=2,
            )

        return path