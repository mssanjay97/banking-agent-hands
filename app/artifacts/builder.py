from pathlib import Path
import json

from app.artifacts.schema import (
    ArtifactInput,
    ArtifactOutput,
    ArtifactStep,
    BusinessOutcome,
    CapabilityArtifact,
    Checkpoint,
)
from app.artifacts.surface import Surface


def build_artifact(
    discovery_file: Path,
    output_file: Path,
    capability_id: str,
    artifact_version: str,
    surface: Surface,
):
    with discovery_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        discovery = json.load(file)

    start_url = discovery["start_url"]
    actions = discovery["actions"]
    goal = discovery.get("goal")

    steps = []

    for action in actions:
        action_type = action["action"]

        value = None
        if action_type not in {"extract", "click"}:
            value = action.get("value")

        steps.append(
            ArtifactStep(
                action=action_type,
                target=action.get("target", {}),
                value=value,
                output=action.get("output"),
            )
        )

    outputs = {}

    for action in actions:
        if action.get("action") != "extract":
            continue

        output_name = action.get("output")

        if output_name:
            outputs[output_name] = ArtifactOutput(
                type="string"
            )

    # Build artifact inputs from LLM-discovered parameters
    inputs = {}

    for parameter in discovery.get("parameters", []):
        name = parameter.get("name")
        parameter_type = parameter.get("type", "string")

        if not name:
            continue

        inputs[name] = ArtifactInput(
            type=parameter_type,
            required=True,
        )

    checkpoint = None

    # Prefer the completion target recorded by the discovery agent.
    for action in actions:
        if action.get("action") == "done" and action.get("target"):
            checkpoint = Checkpoint(
                type="element_present",
                target=action["target"],
            )
            break

    # Fallback if discovery did not record a done target.
    if checkpoint is None:
        for action in reversed(actions):
            action_type = action.get("action")
            target = action.get("target")

            if action_type in {"extract", "click", "fill"} and target:
                checkpoint = Checkpoint(
                    type="element_present",
                    target=target,
                )
                break 

    artifact = CapabilityArtifact(
        id=capability_id,
        version=artifact_version,
        surface=surface,
        inputs=inputs,
        steps=steps,
        outputs=outputs,
        checkpoint=checkpoint,
        business_outcomes=[],
        goal=goal,
        start_url=start_url,
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            artifact.model_dump(),
            file,
            indent=2,
        )

    return output_file