from pathlib import Path
import json


class DiscoveryRecorder:
    def __init__(
        self,
        capability_id: str,
        artifact_version: str,
        goal: str,
        start_url: str,
        surface_type: str,
        surface_vendor: str,
        surface_tenant: str,
        surface_version: str,
        parameter_info=None,
    ):
        self.capability_id = capability_id
        self.artifact_version = artifact_version
        self.goal = goal
        self.start_url = start_url

        self.surface = {
            "type": surface_type,
            "vendor": surface_vendor,
            "tenant": surface_tenant,
            "base_url": start_url,
            "version": surface_version,
        }

        
        self.actions = []
        self.parameter_info = parameter_info or {}

    def record(self, action):
        recorded_action = self._parameterize_value(action.copy())

        if recorded_action.get("action") == "extract":
            recorded_action.pop("value", None)

        self.actions.append(recorded_action)

    def save(
        self,
        output_directory: Path | None = None,
        filename: str | None = None,
    ):
        if output_directory is None:
            output_directory = Path(
                "evidence/discovery"
            )

        if filename is None:
            filename = (
                f"{self.capability_id}"
                f"_v{self.artifact_version}.json"
            )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = output_directory / filename

        artifact = {
            "capability_id": self.capability_id,
            "artifact_version": self.artifact_version,
            "goal": self.goal,
            "start_url": self.start_url,
            "surface": self.surface,
            "parameters": self.parameter_info.get("parameters", []),
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

    def _parameterize_value(self, value):
        if isinstance(value, dict):
            return {
                key: self._parameterize_value(val)
                for key, val in value.items()
            }

        if isinstance(value, list):
            return [
                self._parameterize_value(item)
                for item in value
            ]

        if not isinstance(value, str):
            return value

        parameters = self.parameter_info.get("parameters", [])

        # Longest values first so one parameter cannot partially
        # replace another parameter with a similar value.
        parameters = sorted(
            parameters,
            key=lambda p: len(p.get("value", "")),
            reverse=True,
        )

        for parameter in parameters:
            name = parameter.get("name")
            concrete_value = parameter.get("value")

            if not name or concrete_value is None:
                continue

            token = "{{" + name + "}}"

            # Exact match
            if value == concrete_value:
                return token

            # Embedded value
            value = value.replace(
                concrete_value,
                token,
            )

        return value