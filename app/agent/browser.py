from playwright.async_api import Page


async def observe_page(page: Page) -> dict:
    title = await page.title()
    url = page.url
    body_text = await page.locator("body").inner_text()

    elements = []

    # Broad set of elements that can represent UI controls.
    interactive_elements = page.locator(
        """
        input,
        button,
        a,
        select,
        textarea,
        option,
        [contenteditable="true"],
        [role]
        """
    )

    count = await interactive_elements.count()

    for i in range(count):
        element = interactive_elements.nth(i)

        try:
            tag = await element.evaluate(
                "(el) => el.tagName.toLowerCase()"
            )

            text = ""
            try:
                text = (await element.inner_text()).strip()
            except Exception:
                pass

            aria_label = await element.get_attribute("aria-label")
            element_id = await element.get_attribute("id")
            html_name = await element.get_attribute("name")
            element_type = await element.get_attribute("type")
            placeholder = await element.get_attribute("placeholder")
            role = await element.get_attribute("role")

            accessible_name = await element.evaluate(
                """
                (el) => {
                    if (el.labels && el.labels.length > 0) {
                        return Array.from(el.labels)
                            .map(label => label.innerText.trim())
                            .filter(Boolean)
                            .join(" ");
                    }

                    return (
                        el.getAttribute("aria-label") ||
                        el.getAttribute("aria-labelledby") ||
                        el.getAttribute("placeholder") ||
                        el.innerText ||
                        el.value ||
                        ""
                    ).trim();
                }
                """
            )

            # input_value() is only valid for value-bearing form controls.
            current_value = ""

            if tag in ["input", "textarea", "select"]:
                try:
                    current_value = await element.input_value()
                except Exception:
                    current_value = ""

            checked = None

            if tag == "input":
                input_type = (element_type or "").lower()

                if input_type in ["checkbox", "radio"]:
                    try:
                        checked = await element.is_checked()
                    except Exception:
                        checked = None

            disabled = False

            try:
                disabled = await element.is_disabled()
            except Exception:
                pass

            selected = None

            if tag == "option":
                try:
                    selected = await element.is_checked()
                except Exception:
                    try:
                        selected = await element.get_attribute("selected")
                    except Exception:
                        selected = None

            elements.append(
                {
                    "index": i,
                    "tag": tag,
                    "role": role,
                    "text": text,
                    "accessible_name": accessible_name,
                    "aria_label": aria_label,
                    "id": element_id,
                    "html_name": html_name,
                    "type": element_type,
                    "placeholder": placeholder,
                    "value": current_value,
                    "checked": checked,
                    "selected": selected,
                    "disabled": disabled,
                }
            )

        except Exception:
            # Do not allow one malformed/unusual element
            # to remove other elements from the observation.
            continue

    data_elements = []

    selectors = [
        "[data-field]",
        "[role='alert']",
        "table td",
        "table th",
    ]

    for selector in selectors:
        locator = page.locator(selector)
        count = await locator.count()

        for i in range(count):
            element = locator.nth(i)

            try:
                text = (await element.inner_text()).strip()

                if not text:
                    continue

                data_elements.append(
                    {
                        "selector": selector,
                        "index": i,
                        "text": text,
                        "id": await element.get_attribute("id"),
                        "data_field": await element.get_attribute(
                            "data-field"
                        ),
                        "class": await element.get_attribute(
                            "class"
                        ),
                    }
                )

            except Exception:
                continue

    return {
        "url": url,
        "title": title,
        "text": body_text,
        "interactive_elements": elements,
        "data_elements": data_elements,
    }