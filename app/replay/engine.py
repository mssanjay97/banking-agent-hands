import argparse
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
from app.safety.policy import SafetyPolicy


def load_artifact(
    artifact_path: Path,
) -> dict:
    with artifact_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def parse_inputs(
    values: list[str],
) -> dict:
    inputs = {}

    for item in values:
        if "=" not in item:
            raise ValueError(
                f"Invalid input '{item}'. "
                "Expected format: key=value"
            )

        key, value = item.split("=", 1)

        if not key:
            raise ValueError(
                f"Invalid input '{item}'. "
                "Input name cannot be empty."
            )

        inputs[key] = value

    return inputs


def validate_inputs(
    artifact: dict,
    inputs: dict,
):
    required_inputs = artifact.get(
        "inputs",
        {},
    )

    missing = []

    for name, definition in required_inputs.items():
        if definition.get("required", True):
            if name not in inputs:
                missing.append(name)

    if missing:
        raise ValueError(
            "Missing required inputs: "
            + ", ".join(missing)
        )

    unknown = [
        name
        for name in inputs
        if name not in required_inputs
    ]

    if unknown:
        raise ValueError(
            "Unknown inputs: "
            + ", ".join(unknown)
        )
    
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


def resolve_value(
    value,
    inputs,
):
    if not isinstance(value, str):
        return value

    resolved = value

    for key, input_value in inputs.items():
        token = "{{" + key + "}}"

        resolved = resolved.replace(
            token,
            str(input_value),
        )

    unresolved_tokens = []

    import re

    for token in re.findall(
        r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}",
        resolved,
    ):
        unresolved_tokens.append(token)

    if unresolved_tokens:
        raise ValueError(
            "Unresolved artifact inputs: "
            + ", ".join(sorted(set(unresolved_tokens)))
        )

    return resolved


async def resolve_selector(page, selector):
    if not selector:
        return None

    selector = selector.strip()

    # Semantic text selector
    if selector.startswith("text:"):
        text = selector[len("text:"):].strip()
        return page.get_by_text(text, exact=False)

    # CSS selector
    if selector.startswith("css:"):
        css = selector[len("css:"):].strip()
        return page.locator(css)

    # XPath selector
    if selector.startswith("xpath:"):
        xpath = selector[len("xpath:"):].strip()
        return page.locator(f"xpath={xpath}")

    # Playwright text selector
    if selector.startswith("text="):
        return page.locator(selector)

    # Default: treat unprefixed selector as CSS
    return page.locator(selector)


async def verify_checkpoint(page, checkpoint):
    if not checkpoint:
        return True

    target = checkpoint.get("target", {})

    role = target.get("role")
    name = target.get("name")
    element_id = target.get("id")
    selector = target.get("selector")

    # 1. Semantic role/name
    if role and name:
        try:
            locator = page.get_by_role(role, name=name)
            if await locator.count() > 0:
                return True
        except Exception:
            pass

    # 2. Stable ID
    if element_id:
        try:
            locator = page.locator(f"#{element_id}")
            if await locator.count() > 0:
                return True
        except Exception:
            pass

    # 3. Generic selector resolution
    if selector:
        try:
            locator = await resolve_selector(page, selector)
            if locator and await locator.count() > 0:
                return True
        except Exception:
            pass

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
    policy: SafetyPolicy,
    expected_surface: dict,
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
                expected_surface,
            )

            policy.check_url(base_url)

            await page.goto(base_url)

            for step_number, step in enumerate(
                artifact["steps"],
                start=1,
            ):
                print(
                    f"\n========== REPLAY STEP {step_number} =========="
                )

                action = step.copy()

                if action.get("action") == "done":
                    continue

                if "value" in action:
                    action["value"] = resolve_value(
                        action["value"],
                        inputs,
                    )

                if action["action"] == "navigate":
                    target = action["target"]

                    if target.startswith("/"):
                        action["target"] = (
                            base_url.rstrip("/")
                            + target
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
                            policy,
                        )
                        break

                    except Exception as error:
                        attempt += 1

                        if attempt > max_retries:
                            raise HardFailure(
                                f"Action failed after "
                                f"{max_retries} retries: "
                                f"{error}"
                            )

                        recoverable_error = (
                            RecoverableError(
                                str(error)
                            )
                        )

                        log_event(
                            "recoverable_error",
                            {
                                "step": step_number,
                                "attempt": attempt,
                                "error": str(
                                    recoverable_error
                                ),
                            },
                        )

                        print(
                            f"Recoverable error. "
                            f"Retrying "
                            f"({attempt}/{max_retries})..."
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


            checkpoint = artifact.get(
                "checkpoint"
            )

            checkpoint_ok = True

            if checkpoint:
                checkpoint_ok = (
                    await verify_checkpoint(
                        page,
                        checkpoint,
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
                    "status": (
                        ResultStatus.DRIFT_DETECTED.value
                    ),
                    "error": str(error),
                },
            )

            return {
                "status": (
                    ResultStatus.DRIFT_DETECTED.value
                ),
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Deterministically replay a capability artifact."
    )

    parser.add_argument(
        "--artifact",
        required=True,
        help="Path to the capability artifact JSON.",
    )

    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help=(
            "Runtime input in key=value format. "
            "Repeat for multiple inputs."
        ),
    )

    parser.add_argument(
        "--surface-type",
        required=True,
        help="Runtime surface type.",
    )

    parser.add_argument(
        "--surface-vendor",
        required=True,
        help="Runtime surface vendor.",
    )

    parser.add_argument(
        "--surface-tenant",
        required=True,
        help="Runtime surface tenant.",
    )

    parser.add_argument(
        "--surface-version",
        required=True,
        help="Runtime surface version.",
    )

    parser.add_argument(
        "--allowed-domain",
        action="append",
        required=True,
        help=(
            "Allowed navigation domain. "
            "Repeat for multiple domains."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    artifact = load_artifact(
        Path(args.artifact)
    )

    inputs = parse_inputs(
        args.input
    )

    validate_inputs(
        artifact,
        inputs,
    )

    policy = SafetyPolicy(
        allowed_domains=args.allowed_domain,
        allowed_actions=[
            "navigate",
            "fill",
            "clear",
            "select",
            "check",
            "uncheck",
            "click",
            "extract",
        ],
        risky_actions=[],
    )

    expected_surface = {
        "type": args.surface_type,
        "vendor": args.surface_vendor,
        "tenant": args.surface_tenant,
        "version": args.surface_version,
    }

    result = asyncio.run(
        replay_artifact(
            artifact=artifact,
            inputs=inputs,
            policy=policy,
            expected_surface=expected_surface,
        )
    )

    print(
        "\n========== REPLAY COMPLETE =========="
    )

    print("RESULT:")
    print(result)


if __name__ == "__main__":
    main()