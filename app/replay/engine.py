import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

from app.agent.actions import execute_action
from app.replay.errors import (
    BusinessOutcome,
    DriftDetected,
    HardFailure,
    RecoverableError,
    ResultStatus,
)
from app.replay.evidence import capture_failure_screenshot
from app.replay.logging import log_event


ARTIFACT_PATH = Path(
    "evidence/discovery/member_balance_lookup.json"
)


def load_artifact() -> dict:
    with ARTIFACT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)

def validate_surface(
    artifact: dict,
    expected_surface: dict,
):
    artifact_surface = artifact["surface"]

    for field in [
        "type",
        "vendor",
        "tenant",
        "version",
    ]:
        if artifact_surface[field] != expected_surface[field]:
            raise DriftDetected(
                f"Surface drift detected for {field}: "
                f"artifact={artifact_surface[field]}, "
                f"runtime={expected_surface[field]}"
            )


def resolve_value(value, inputs):
    if not isinstance(value, str):
        return value

    for key, input_value in inputs.items():
        value = value.replace(
            "{{" + key + "}}",
            str(input_value),
        )

    return value


async def verify_checkpoint(
    page,
    checkpoint: dict,
):
    target = checkpoint["target"]

    role = target.get("role")
    name = target.get("name")

    if role and name:
        locator = page.get_by_role(
            role,
            name=name,
        )

        if await locator.count() > 0:
            return True

    selector = target.get("selector")

    if selector:
        locator = page.locator(selector)

        if await locator.count() > 0:
            return True

    element_id = target.get("id")

    if element_id:
        locator = page.locator(
            f"#{element_id}"
        )

        if await locator.count() > 0:
            return True

    return False


async def detect_business_outcome(
    page,
    business_outcomes: list,
):
    alert = page.locator(
        '[role="alert"]'
    )

    if await alert.count() == 0:
        return None

    text = (
        await alert.first.inner_text()
    ).strip()

    for outcome in business_outcomes:
        signal = outcome["signal"]

        if signal.lower() in text.lower():
            return outcome["status"]

    return None

async def replay_artifact(
    artifact: dict,
    inputs: dict,
):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False
        )

        page = await browser.new_page()


        surface = artifact["surface"]

        if surface["type"] != "web":
            raise ValueError(
                f"Unsupported surface type: {surface['type']}"
            )

        base_url = surface["base_url"]

        

        outputs = {}

        try:

            validate_surface(
                        artifact,
                        {
                            "type": "web",
                            "vendor": "demo-core-banking",
                            "tenant": "demo",
                            "version": "1.0",
                        },
                    )
            
            for step_number, step in enumerate(
                artifact["steps"],
                start=1,
            ):
                print(
                    f"\n========== REPLAY STEP {step_number} =========="
                )

                action = step.copy()

                if "value" in action:
                    action["value"] = resolve_value(
                        action["value"],
                        inputs,
                    )

                if action["action"] == "navigate":
                    target = action["target"]

                    if target.startswith("/"):
                        action["target"] = (
                            base_url + target
                        )

                print("ACTION:")
                print(action)

                log_event(
                    "action_started",
                    {
                        "step": step_number,
                        "action": action,
                    },
                )

                max_retries = 2
                attempt = 0

                while True:
                    try:
                        result = await execute_action(
                            page,
                            action,
                        )
                        break

                    except Exception as error:
                        attempt += 1

                        if attempt > max_retries:
                            raise HardFailure(
                                f"Action failed after {max_retries} retries: "
                                f"{error}"
                            )

                        recoverable_error = RecoverableError(
                            str(error)
                        )

                        log_event(
                            "recoverable_error",
                            {
                                "step": step_number,
                                "attempt": attempt,
                                "error": str(recoverable_error),
                            },
                        )

                        print(
                            f"Recoverable error. "
                            f"Retrying ({attempt}/{max_retries})..."
                        )

                        await asyncio.sleep(1)


                print("RESULT:")
                print(result)

                log_event(
                    "action_completed",
                    {
                        "step": step_number,
                        "result": result,
                    },
                )

                business_outcome = (
                    await detect_business_outcome(
                        page,
                        artifact.get(
                            "business_outcomes",
                            [],
                        ),
                    )
                )

                if business_outcome:
                    log_event(
                        "business_outcome",
                        {
                            "status": (
                                ResultStatus
                                .BUSINESS_OUTCOME
                                .value
                            ),
                            "error": business_outcome,
                        },
                    )

                    raise BusinessOutcome(
                        business_outcome
                    )

                if action["action"] == "extract":
                    output_name = step["output"]

                    outputs[output_name] = (
                        result["value"]
                    )

            checkpoint_ok = (
                await verify_checkpoint(
                    page,
                    artifact["checkpoint"],
                )
            )

            print("\nCHECKPOINT:")
            print(checkpoint_ok)

            if not checkpoint_ok:
                raise HardFailure(
                    "Checkpoint verification failed."
                )

            log_event(
                "replay_completed",
                {
                    "status": (
                        ResultStatus.SUCCESS.value
                    ),
                    "outputs": outputs,
                },
            )

            return {
                "status": (
                    ResultStatus.SUCCESS.value
                ),
                "outputs": outputs,
            }

        except BusinessOutcome as error:
            return {
                "status": (
                    ResultStatus.BUSINESS_OUTCOME.value
                ),
                "error": str(error),
                "outputs": {},
            }

        except DriftDetected as error:
            log_event(
                "drift_detected",
                {
                    "status": ResultStatus.DRIFT_DETECTED.value,
                    "error": str(error),
                },
            )

            return {
                "status": ResultStatus.DRIFT_DETECTED.value,
                "error": str(error),
                "outputs": {},
            }

        except HardFailure as error:
            screenshot_path = (
                await capture_failure_screenshot(
                    page,
                    str(error),
                )
            )

            log_event(
                "replay_failed",
                {
                    "status": (
                        ResultStatus.HARD_FAILURE.value
                    ),
                    "error": str(error),
                    "screenshot": screenshot_path,
                },
            )

            return {
                "status": (
                    ResultStatus.HARD_FAILURE.value
                ),
                "error": str(error),
                "screenshot": screenshot_path,
                "outputs": {},
            }

        finally:
            await browser.close()


if __name__ == "__main__":
    artifact = load_artifact()

    result = asyncio.run(
        replay_artifact(
            artifact,
            {
                "member_id": "67890",
            },
        )
    )

    print(
        "\n========== REPLAY COMPLETE =========="
    )

    print("RESULT:")
    print(result)