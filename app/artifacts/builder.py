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


DISCOVERY_FILE = Path(
    "evidence/discovery/discovery_actions.json"
)

OUTPUT_FILE = Path(
    "evidence/discovery/member_balance_lookup_generated.json"
)


def build_artifact():
    with DISCOVERY_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        discovery = json.load(file)

    start_url = discovery["start_url"]
    actions = discovery["actions"]

    steps = []

    steps.append(
        ArtifactStep(
            action="navigate",
            target=start_url,
        )
    )

    for action in actions:
        action_copy = action.copy()

        output = None

        if action_copy["action"] == "extract":
            output = "savings_balance"

        steps.append(
            ArtifactStep(
                action=action_copy["action"],
                target=action_copy.get("target", {}),
                value=action_copy.get("value"),
                output=output,
            )
        )

    artifact = CapabilityArtifact(
        id="member-balance-lookup",
        version="1.0",
        surface=Surface(
            type="web",
            vendor="demo-core-banking",
            tenant="demo",
            base_url="http://127.0.0.1:3000",
            version="1.0",
        ),
        inputs={
            "member_id": ArtifactInput(
                type="string",
                required=True,
            )
        },
        steps=steps,
        outputs={
            "savings_balance": ArtifactOutput(
                type="string"
            )
        },
        checkpoint=Checkpoint(
            type="element_present",
            target={
                "selector": "[data-field='savings-balance']"
            },
        ),
        business_outcomes=[
            BusinessOutcome(
                signal="Member not found.",
                status="MEMBER_NOT_FOUND",
            )
        ],
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            artifact.model_dump(),
            file,
            indent=2,
        )

    return OUTPUT_FILE


if __name__ == "__main__":
    path = build_artifact()
    print(f"Artifact saved to: {path}")