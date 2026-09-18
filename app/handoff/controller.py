import asyncio
from pathlib import Path
from datetime import datetime

from playwright.async_api import Page

from app.handoff.manager import (
    create_handoff_request,
    is_handoff_complete,
)


HANDOFF_EVIDENCE_DIR = Path("evidence/handoff")


async def capture_handoff_screenshot(
    page: Page,
) -> str:
    """
    Capture the current browser state before human intervention.
    """

    HANDOFF_EVIDENCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.utcnow().strftime(
        "%Y%m%d_%H%M%S"
    )

    path = (
        HANDOFF_EVIDENCE_DIR
        / f"{timestamp}_handoff.png"
    )

    await page.screenshot(
        path=str(path),
        full_page=True,
    )

    return str(path)


async def wait_for_human(
    goal: str,
    step: int,
    reason: str,
    page: Page,
    observation: dict | None = None,
    poll_seconds: float = 1.0,
):
    """
    Pause automation while keeping the existing browser session alive.
    """

    screenshot = await capture_handoff_screenshot(
        page
    )

    recovery_hint = (
        "Review the current browser state and complete the missing "
        "interaction manually, then signal that the handoff is complete."
    )

    if observation:
        recovery_hint = (
            "Review the current browser state shown in the screenshot. "
            "Complete the interaction required to move the workflow "
            "forward, then signal that the handoff is complete."
        )

    request_path = create_handoff_request(
        goal=goal,
        step=step,
        reason=reason,
        screenshot=screenshot,
        current_url=page.url,
        page_title=await page.title(),
        recovery_hint=recovery_hint,
    )

    print("\n========== HUMAN HANDOFF ==========")
    print("Automation is paused.")
    print(f"Reason: {reason}")
    print(f"Screenshot: {screenshot}")
    print(f"Request: {request_path}")
    print("Perform the required action in the open browser.")
    print("Then mark the handoff as complete.")

    while not is_handoff_complete():
        await asyncio.sleep(poll_seconds)

    print("\n========== HUMAN HANDOFF COMPLETE ==========")
    print("Resuming automation.")

handoff_to_human = wait_for_human