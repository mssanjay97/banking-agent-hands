from playwright.async_api import Page

from app.safety.policy import SafetyPolicy


async def execute_action(
    page: Page,
    action: dict,
    policy: SafetyPolicy,
):
    """
    Execute one structured browser action.

    Supported actions:
        navigate
        fill
        clear
        select
        check
        uncheck
        click
        extract

    The LLM decides which action to perform.
    This layer only executes the requested action.
    """

    policy.check_action(action)

    action_type = action["action"]

    # ---------------------------------------------------------
    # NAVIGATE
    # ---------------------------------------------------------

    if action_type == "navigate":
        url = action.get("value")

        if not isinstance(url, str):
            raise ValueError(
                f"Navigate URL must be a string, got: "
                f"{type(url).__name__}: {url!r}"
            )

        url = url.strip()

        if not url:
            raise ValueError(
                "Navigate action requires a non-empty URL."
            )

        policy.check_url(url)

        await page.goto(
            url,
            wait_until="domcontentloaded",
        )

        return {
            "status": "success",
            "action": "navigate",
            "url": page.url,
        }

    # ---------------------------------------------------------
    # FILL
    # ---------------------------------------------------------

    if action_type == "fill":
        target = action["target"]
        value = action.get("value")

        if value is None:
            raise ValueError(
                "fill action requires a value"
            )

        locator = await find_locator(
            page,
            target,
        )

        await locator.fill(str(value))

        return {
            "status": "success",
            "action": "fill",
            "target": target,
        }

    # ---------------------------------------------------------
    # CLEAR
    # ---------------------------------------------------------

    if action_type == "clear":
        target = action["target"]

        locator = await find_locator(
            page,
            target,
        )

        await locator.fill("")

        return {
            "status": "success",
            "action": "clear",
            "target": target,
        }

    # ---------------------------------------------------------
    # SELECT
    # ---------------------------------------------------------

    if action_type == "select":
        target = action["target"]
        value = action.get("value")

        if value is None:
            raise ValueError(
                "select action requires a value"
            )

        locator = await find_locator(
            page,
            target,
        )

        tag = await locator.evaluate(
            "(el) => el.tagName.toLowerCase()"
        )

        if tag != "select":
            raise ValueError(
                "select action requires a <select> element"
            )

        await locator.select_option(
            str(value)
        )

        return {
            "status": "success",
            "action": "select",
            "target": target,
            "value": str(value),
        }

    # ---------------------------------------------------------
    # CHECK
    # ---------------------------------------------------------

    if action_type == "check":
        target = action["target"]

        locator = await find_locator(
            page,
            target,
        )

        await locator.check()

        return {
            "status": "success",
            "action": "check",
            "target": target,
        }

    # ---------------------------------------------------------
    # UNCHECK
    # ---------------------------------------------------------

    if action_type == "uncheck":
        target = action["target"]

        locator = await find_locator(
            page,
            target,
        )

        await locator.uncheck()

        return {
            "status": "success",
            "action": "uncheck",
            "target": target,
        }

    # ---------------------------------------------------------
    # CLICK
    # ---------------------------------------------------------

    if action_type == "click":
        target = action["target"]

        locator = await find_locator(
            page,
            target,
        )

        await locator.click()

        return {
            "status": "success",
            "action": "click",
            "target": target,
        }

    # ---------------------------------------------------------
    # EXTRACT
    # ---------------------------------------------------------

    if action_type == "extract":
        target = action["target"]

        locator = await find_locator(
            page,
            target,
        )

        value = await locator.inner_text()

        return {
            "status": "success",
            "action": "extract",
            "target": target,
            "value": value.strip(),
        }

    raise ValueError(
        f"Unsupported action: {action_type}"
    )


async def find_locator(
    page: Page,
    target: dict,
):
    """
    Resolve a structured target.

    Resolution order:
        1. Accessible role + name
        2. HTML id
        3. CSS selector

    The target is produced from the observed browser
    surface. No application-specific selectors are
    generated here.
    """

    if not target:
        raise ValueError(
            "Action target is required"
        )

    role = target.get("role")
    name = target.get("name")

    # ---------------------------------------------------------
    # 1. Accessible role + accessible name
    # ---------------------------------------------------------

    if role and name:
        locator = page.get_by_role(
            role,
            name=name,
        )

        if await locator.count() > 0:
            return locator.first

    # ---------------------------------------------------------
    # 2. HTML id
    # ---------------------------------------------------------

    element_id = target.get("id")

    if element_id:
        locator = page.locator(
            f"#{element_id}"
        )

        if await locator.count() > 0:
            return locator.first

    # ---------------------------------------------------------
    # 3. CSS selector
    # ---------------------------------------------------------

    selector = target.get("selector")

    if selector:
        locator = page.locator(
            selector
        )

        if await locator.count() > 0:
            return locator.first

    raise ValueError(
        f"Could not find target element: {target}"
    )