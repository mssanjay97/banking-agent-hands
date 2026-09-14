from datetime import datetime
from pathlib import Path
import re

from playwright.async_api import Page


FAILURE_DIR = Path("evidence/failures")


def _safe_filename(text: str, max_length: int = 80) -> str:
    """
    Convert arbitrary error text into a filename-safe string.
    Works across Windows and Unix-like systems.
    """
    text = re.sub(r"[^a-zA-Z0-9._-]+", "_", text)
    text = text.strip("._-")

    if not text:
        text = "failure"

    return text[:max_length]


async def capture_failure_screenshot(
    page: Page,
    reason: str,
) -> str:
    FAILURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.utcnow().strftime(
        "%Y%m%d_%H%M%S"
    )

    safe_reason = _safe_filename(reason)

    filename = (
        f"{timestamp}_{safe_reason}.png"
    )

    path = FAILURE_DIR / filename

    await page.screenshot(
        path=str(path),
        full_page=True,
    )

    return str(path)