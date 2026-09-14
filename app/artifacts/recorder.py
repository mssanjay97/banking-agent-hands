import json
from pathlib import Path

from app.artifacts.schema import (
    ArtifactInput,
    ArtifactOutput,
    ArtifactStep,
    CapabilityArtifact,
    Checkpoint,
)


ARTIFACT_DIR = Path("evidence/discovery")


def save_member_balance_artifact() -> Path:
    """
    Create and save the reusable member balance lookup capability.
    """

    artifact = CapabilityArtifact(
        id="member_balance_lookup",
        version="1.0.0",
        target={
            "app": "demo-core-banking",
            "base_url": "http://127.0.0.1:3000",
        },
        inputs={
            "member_id": ArtifactInput(
                type="string",
                required=True,
            )
        },
        steps=[
            ArtifactStep(
                action="navigate",
                target="/members",
            ),
            ArtifactStep(
                action="fill",
                target={
                    "role": "textbox",
                    "name": "Member ID",
                },
                value="{{member_id}}",
            ),
            ArtifactStep(
                action="click",
                target={
                    "role": "button",
                    "name": "Search",
                },
            ),
            ArtifactStep(
                action="extract",
                target={
                    "selector": "[data-field='savings-balance']",
                },
                output="savings_balance",
            ),
        ],
        outputs={
            "savings_balance": ArtifactOutput(
                type="currency",
            )
        },
        checkpoint=Checkpoint(
            type="element_visible",
            target={
                "role": "heading",
                "name": "Member Details",
            },
        ),
    )

    ARTIFACT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = ARTIFACT_DIR / "member_balance_lookup.json"

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            artifact.model_dump(),
            file,
            indent=2,
        )

    return output_path


if __name__ == "__main__":
    path = save_member_balance_artifact()
    print(f"Artifact saved to: {path}")