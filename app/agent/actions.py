from playwright.async_api import Page
from app.safety.policy import SafetyPolicy

DEFAULT_POLICY = SafetyPolicy(
    allowed_domains=[
        "127.0.0.1",
        "localhost",
    ],
    allowed_actions=[
        "navigate",
        "fill",
        "click",
        "extract",
    ],
    risky_actions=[],
)

async def execute_action(page: Page,action: dict, policy: SafetyPolicy = DEFAULT_POLICY):    
    """
    Execute one structured browser action.

    Supported actions:
    - navigate
    - fill
    - click
    - extract
    """    
    policy.check_action(action)

    if action["action"] == "navigate":
        policy.check_url(action["target"])

    action_type = action["action"]

    if action_type == "navigate":
        target = action["target"]

        await page.goto(target)

        return {
            "status": "success",
            "action": "navigate",
            "target": target,
        }

    if action_type == "fill":
        target = action["target"]
        value = action["value"]

        locator = await find_locator(page, target)

        await locator.fill(value)

        return {
            "status": "success",
            "action": "fill",
            "target": target,
        }

    if action_type == "click":
        target = action["target"]

        locator = await find_locator(page, target)

        await locator.click()

        return {
            "status": "success",
            "action": "click",
            "target": target,
        }

    if action_type == "extract":
        target = action["target"]

        locator = await find_locator(page, target)

        value = await locator.inner_text()

        return {
            "status": "success",
            "action": "extract",
            "target": target,
            "value": value.strip(),
        }

    raise ValueError(f"Unsupported action: {action_type}")


async def find_locator(page: Page, target: dict):
    """
    Resolve an LLM-generated target using multiple locator strategies.

    This makes the agent more tolerant of small differences in
    how the LLM describes an element.
    """

    role = target.get("role")
    name = target.get("name")

    # 1. Preferred: accessible role + name.
    if role and name:
        locator = page.get_by_role(
            role,
            name=name,
        )

        if await locator.count() > 0:
            return locator.first

    # 2. If the target contains an HTML id.
    element_id = target.get("id")

    if element_id:
        locator = page.locator(f"#{element_id}")

        if await locator.count() > 0:
            return locator.first

    # 3. If the target contains a CSS selector.
    selector = target.get("selector")

    if selector:
        locator = page.locator(selector)

        if await locator.count() > 0:
            return locator.first

    raise ValueError(
        f"Could not find target element: {target}"
    )