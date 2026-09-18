import argparse
import asyncio
import json
from pathlib import Path

from app.artifacts.surface import Surface
from playwright.async_api import async_playwright

from app.agent.browser import observe_page
from app.agent.actions import execute_action
from app.agent.llm import ask_llm, extract_parameters
from app.safety.policy import SafetyPolicy

from app.artifacts.discovery_recorder import DiscoveryRecorder
from app.artifacts.builder import build_artifact

from app.handoff.controller import handoff_to_human


ALLOWED_ACTIONS = [
    "navigate",
    "fill",
    "clear",
    "select",
    "check",
    "uncheck",
    "click",
    "extract",
    "done",
]


async def verify_completion(
    page,
    target,
):
    if not target:
        return False

    role = target.get("role")
    name = target.get("name")
    selector = target.get("selector")
    element_id = target.get("id")

    # 1. Valid ARIA role + accessible name
    if (
        role
        and role != "text"
        and name
    ):
        try:
            locator = page.get_by_role(
                role,
                name=name,
            )

            if await locator.count() > 0:
                return True

        except Exception:
            pass

    # 2. CSS selector
    if (
        selector
        and selector != "text"
    ):
        try:
            locator = page.locator(
                selector
            )

            if await locator.count() > 0:
                return True

        except Exception:
            pass

    # 3. Element ID
    if element_id:
        try:
            locator = page.locator(
                f"#{element_id}"
            )

            if await locator.count() > 0:
                return True

        except Exception:
            pass

    # 4. Generic textual evidence
    #
    # "text" is not an ARIA role or CSS selector.
    # If the LLM identifies visible completion evidence
    # by text, search for that text directly.
    if name:
        try:
            locator = page.get_by_text(
                name,
                exact=False,
            )

            if await locator.count() > 0:
                return True

        except Exception:
            pass

    return False

def validate_llm_action(
    action: dict,
    observation: dict,
) -> dict:

    if not isinstance(action, dict):
        raise ValueError(
            "LLM response must be a JSON object."
        )

    action_type = action.get("action")

    if not isinstance(action_type, str):
        raise ValueError(
            "LLM action must contain a string 'action'."
        )

    target = action.get("target")

    if target is None:
        target = {}

    if not isinstance(target, dict):
        raise ValueError(
            "LLM action target must be an object."
        )

    # ---------------------------------------------------------
    # Never allow the LLM to invent IDs/selectors
    # ---------------------------------------------------------

    observed_elements = (
        observation.get("interactive_elements", [])
    )

    observed_data = (
        observation.get("data_elements", [])
    )

    observed_ids = {
        element.get("id")
        for element in observed_elements
        if element.get("id")
    }

    observed_ids.update(
        element.get("id")
        for element in observed_data
        if element.get("id")
    )

    requested_id = target.get("id")

    if requested_id and requested_id not in observed_ids:
        target["id"] = None

    # ---------------------------------------------------------
    # Navigation URL must be a string
    # ---------------------------------------------------------

    if action_type == "navigate":

        url = action.get("value")

        if not isinstance(url, str):
            raise ValueError(
                "Navigate action value must be a string."
            )

        action["value"] = url.strip()

    # ---------------------------------------------------------
    # Fill value must be a scalar/string
    # ---------------------------------------------------------

    if action_type == "fill":

        value = action.get("value")

        if value is None:
            raise ValueError(
                "Fill action requires a value."
            )

        if isinstance(value, (dict, list)):
            raise ValueError(
                "Fill value cannot be an object or list."
            )

        action["value"] = str(value)

    # ---------------------------------------------------------
    # Select value must be scalar
    # ---------------------------------------------------------

    if action_type == "select":

        value = action.get("value")

        if value is None:
            raise ValueError(
                "Select action requires a value."
            )

        if isinstance(value, (dict, list)):
            raise ValueError(
                "Select value cannot be an object or list."
            )

    action["target"] = target

    return action


async def run_agent(
    goal,
    start_url,
    capability_id,
    artifact_version,
    surface_type,
    surface_vendor,
    surface_tenant,
    surface_version,
    max_steps,
    inputs=None,
):
    """
    Run the LLM-driven discovery loop.

    Flow:

        observe
           ↓
        decide
           ↓
        act
           ↓
        observe
           ↓
        ...
           ↓
        done
           ↓
        verify completion
           ↓
        build artifact
    """

    parameter_info = await extract_parameters(goal)

    print("\nDiscovered parameters:")
    print(json.dumps(parameter_info, indent=2))


    policy = SafetyPolicy(
        allowed_domains=[
            "127.0.0.1",
            "localhost",
        ],
        allowed_actions=ALLOWED_ACTIONS,
        risky_actions=[],
    )

    recorder = DiscoveryRecorder(
        capability_id=capability_id,
        artifact_version=artifact_version,
        goal=goal,
        start_url=start_url,
        surface_type=surface_type,
        surface_vendor=surface_vendor,
        surface_tenant=surface_tenant,
        surface_version=surface_version,
        parameter_info=parameter_info,
    )

    previous_action = None
    previous_result = None

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            headless=False,
        )

        page = await browser.new_page()

        try:
            # -------------------------------------------------
            # Initial navigation
            # -------------------------------------------------

            policy.check_url(start_url)

            await page.goto(start_url)

            # -------------------------------------------------
            # Main agent loop
            # -------------------------------------------------

            for step in range(
                1,
                max_steps + 1,
            ):

                print()
                print(
                    f"========== STEP {step} =========="
                )

                # ---------------------------------------------
                # Observe
                # ---------------------------------------------

                observation = await observe_page(
                    page
                )

                # print(
                #     json.dumps(
                #         observation,
                #         indent=2,
                #     )
                # )

                # ---------------------------------------------
                # Ask LLM for exactly one action
                # ---------------------------------------------

                try:
                    action = await ask_llm(
                        goal=goal,
                        observation=observation,
                        previous_action=previous_action,
                        previous_result=previous_result,
                    )

                    action = validate_llm_action(
                        action,
                        observation,
                    )

                except asyncio.TimeoutError:

                    print()
                    print(
                        "LLM decision timed out."
                    )

                    await handoff_to_human(
                        goal=goal,
                        step=step,
                        reason=(
                            "LLM decision timed out."
                        ),
                        page=page,
                        observation=observation,
                    )
                    

                    return {
                        "status": "HANDOFF",
                        "reason": "LLM timeout",
                    }

                print()
                print(
                    "LLM ACTION:"
                )

                print(
                    json.dumps(
                        action,
                        indent=2,
                    )
                )

                action_type = action.get(
                    "action"
                )

                # ---------------------------------------------
                # Validate action type
                # ---------------------------------------------

                if action_type not in ALLOWED_ACTIONS:

                    raise ValueError(
                        f"LLM returned unsupported action: "
                        f"{action_type}"
                    )

                # ---------------------------------------------
                # DONE
                # ---------------------------------------------

                if action_type == "done":

                    completion_target = (
                        action.get(
                            "target"
                        )
                    )

                    verified = (
                        await verify_completion(
                            page,
                            completion_target,
                        )
                    )

                    if not verified:

                        print()
                        print(
                            "DONE REJECTED:"
                        )

                        print(
                            "Completion target "
                            "was not found on the "
                            "current page."
                        )

                        previous_action = action

                        previous_result = {
                            "status": "completion_not_verified",
                            "message": (
                                "The proposed completion "
                                "target was not observable "
                                "on the current page."
                            ),
                        }

                        continue

                    # -----------------------------------------
                    # Successful discovery
                    # -----------------------------------------

                    print()
                    print(
                        "========== GOAL COMPLETE =========="
                    )

                    recorder.record(
                        action
                    )

                    discovery_path = recorder.save()

                    print("DISCOVERY ACTIONS SAVED:")
                    print(discovery_path)

                    artifact_path = Path(
                        "evidence/discovery",
                        f"{capability_id}_v{artifact_version}.artifact.json"
                    )

                    build_artifact(
                        discovery_file=discovery_path,
                        output_file=artifact_path,
                        capability_id=capability_id,
                        artifact_version=artifact_version,
                        surface=Surface(
                            type=surface_type,
                            vendor=surface_vendor,
                            tenant=surface_tenant,
                            base_url=start_url,
                            version=surface_version,
                        ),
                    )

                    print("CAPABILITY ARTIFACT SAVED:")
                    print(artifact_path) 
                    print()
                    print(
                        "Discovery saved:"
                    )

                    print(
                        discovery_path
                    )

                    print()
                    print(
                        "Artifact saved:"
                    )

                    print(
                        artifact_path
                    )

                    return {
                        "status": "SUCCESS",
                        "discovery": str(
                            discovery_path
                        ),
                        "artifact": str(
                            artifact_path
                        ),
                    }

                # ---------------------------------------------
                # Normal browser action
                # ---------------------------------------------

                try:

                    result = (
                        await execute_action(
                            page,
                            action,
                            policy,
                        )
                    )

                except Exception as exc:

                    print()
                    print(
                        "ACTION FAILED:"
                    )

                    print(
                        str(exc)
                    )


                    await handoff_to_human(
                        goal=goal,
                        step=step,
                        reason=str(exc),
                        page=page,
                        observation=observation,
                    )

                    return {
                        "status": "HANDOFF",
                        "reason": str(exc),
                    }

                print()
                print(
                    "ACTION RESULT:"
                )

                print(
                    json.dumps(
                        result,
                        indent=2,
                    )
                )

                # ---------------------------------------------
                # Record successful browser action
                # ---------------------------------------------

                recorder.record(
                    action
                )

                # ---------------------------------------------
                # Remember previous state
                # ---------------------------------------------

                previous_action = action
                previous_result = result

            # -------------------------------------------------
            # Max-step stopping condition
            # -------------------------------------------------

            print()
            print(
                "========== MAX STEPS REACHED =========="
            )


            await handoff_to_human(
                goal=goal,
                step=step,
                reason=(
                    "Maximum agent steps reached "
                    "without verified completion."
                ),
                page=page,
                observation=observation,
            )

            return {
                "status": "HANDOFF",
                "reason": "Maximum steps reached",
            }

        finally:
            await browser.close()


def parse_inputs(
    values: list[str],
) -> dict:
    """
    Parse repeated:

        --input key=value

    arguments into a dictionary.
    """

    result = {}

    for value in values:

        if "=" not in value:
            raise ValueError(
                "Input must use key=value format: "
                f"{value}"
            )

        key, input_value = value.split(
            "=",
            1,
        )

        result[key] = input_value

    return result


def main():

    parser = argparse.ArgumentParser(
        description=(
            "LLM-driven computer-use discovery agent"
        )
    )

    parser.add_argument(
        "--goal",
        required=True,
    )

    parser.add_argument(
        "--start-url",
        required=True,
    )

    parser.add_argument(
        "--capability-id",
        required=True,
    )

    parser.add_argument(
        "--artifact-version",
        required=True,
    )

    parser.add_argument(
        "--surface-type",
        required=True,
    )

    parser.add_argument(
        "--surface-vendor",
        required=True,
    )

    parser.add_argument(
        "--surface-tenant",
        required=True,
    )

    parser.add_argument(
        "--surface-version",
        required=True,
    )

    parser.add_argument(
        "--input",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=15,
    )

    args = parser.parse_args()

    asyncio.run(
        run_agent(
            goal=args.goal,
            start_url=args.start_url,
            capability_id=args.capability_id,
            artifact_version=args.artifact_version,
            surface_type=args.surface_type,
            surface_vendor=args.surface_vendor,
            surface_tenant=args.surface_tenant,
            surface_version=args.surface_version,
            max_steps=args.max_steps,
        )
    )


if __name__ == "__main__":
    main()