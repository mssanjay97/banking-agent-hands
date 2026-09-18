from playwright.async_api import Page


# Common implicit HTML roles.
# This is about browser semantics, not any particular application.
IMPLICIT_ROLES = {
    "a": "link",
    "button": "button",
    "select": "combobox",
    "textarea": "textbox",
    "img": "img",
    "nav": "navigation",
    "main": "main",
    "header": "banner",
    "footer": "contentinfo",
    "form": "form",
}


async def observe_page(page: Page) -> dict:
    """
    Observe the current browser surface.

    The observation is intentionally generic:
    - page metadata
    - visible page text
    - interactive controls
    - form-control state
    - select options
    - semantic roles/names
    - useful stable attributes
    """

    title = await page.title()
    url = page.url

    body_text = await page.locator("body").inner_text()

    elements = []

    interactive_elements = page.locator(
        """
        input,
        button,
        a,
        select,
        textarea,
        [contenteditable="true"],
        [role]
        """
    )

    count = await interactive_elements.count()

    for i in range(count):
        element = interactive_elements.nth(i)

        try:
            element_data = await _observe_element(
                element,
                i,
            )

            if element_data:
                elements.append(element_data)

        except Exception:
            # One malformed element should never destroy
            # the complete page observation.
            continue

    data_elements = await _observe_data_elements(page)

    return {
        "url": url,
        "title": title,
        "text": body_text,
        "interactive_elements": elements,
        "data_elements": data_elements,
    }


async def _observe_element(
    element,
    index: int,
) -> dict:
    """
    Build a generic semantic representation of one
    interactive element.
    """

    tag = (
        await element.evaluate(
            "(el) => el.tagName.toLowerCase()"
        )
    )

    explicit_role = await element.get_attribute("role")

    role = explicit_role or IMPLICIT_ROLES.get(tag)

    text = ""

    try:
        text = (
            await element.inner_text()
        ).strip()
    except Exception:
        pass

    aria_label = await element.get_attribute(
        "aria-label"
    )

    aria_labelledby = await element.get_attribute(
        "aria-labelledby"
    )

    element_id = await element.get_attribute(
        "id"
    )

    html_name = await element.get_attribute(
        "name"
    )

    element_type = await element.get_attribute(
        "type"
    )

    placeholder = await element.get_attribute(
        "placeholder"
    )

    value = await element.get_attribute(
        "value"
    )

    disabled = False

    try:
        disabled = await element.is_disabled()
    except Exception:
        pass

    visible = True

    try:
        visible = await element.is_visible()
    except Exception:
        pass

    checked = None

    if tag == "input":
        input_type = (
            element_type or "text"
        ).lower()

        if input_type in {
            "checkbox",
            "radio",
        }:
            try:
                checked = await element.is_checked()
            except Exception:
                checked = None

    # For normal form controls, input_value()
    # gives the actual current value.
    current_value = ""

    if tag in {
        "input",
        "textarea",
        "select",
    }:
        try:
            current_value = (
                await element.input_value()
            )
        except Exception:
            current_value = value or ""

    accessible_name = (
        await _get_accessible_name(
            element
        )
    )

    data = {
        "index": index,
        "tag": tag,
        "role": role,
        "text": text,
        "accessible_name": accessible_name,
        "aria_label": aria_label,
        "aria_labelledby": aria_labelledby,
        "id": element_id,
        "html_name": html_name,
        "type": element_type,
        "placeholder": placeholder,
        "value": current_value,
        "checked": checked,
        "disabled": disabled,
        "visible": visible,
    }

    # Native select/dropdown information.
    if tag == "select":
        data["multiple"] = (
            await element.get_attribute(
                "multiple"
            )
            is not None
        )

        data["options"] = (
            await _observe_select_options(
                element
            )
        )

    # File inputs should be identified explicitly.
    if (
        tag == "input"
        and (element_type or "").lower()
        == "file"
    ):
        data["input_kind"] = "file"

    # Contenteditable controls need their own indication.
    if (
        await element.get_attribute(
            "contenteditable"
        )
    ) == "true":
        data["input_kind"] = "contenteditable"

    return data


async def _get_accessible_name(
    element,
) -> str:
    """
    Obtain a useful accessible name for an element.

    Preference:
    1. associated <label>
    2. aria-label
    3. aria-labelledby text
    4. placeholder
    5. visible text
    6. current value
    """

    try:
        name = await element.evaluate(
            """
            (el) => {
                function clean(value) {
                    return (value || "")
                        .replace(/\\\\s+/g, " ")
                        .trim();
                }

                // Explicit aria-label.
                const ariaLabel =
                    el.getAttribute("aria-label");

                if (ariaLabel) {
                    return clean(ariaLabel);
                }

                // aria-labelledby.
                const labelledBy =
                    el.getAttribute(
                        "aria-labelledby"
                    );

                if (labelledBy) {
                    const parts =
                        labelledBy
                            .split(/\\\\s+/)
                            .map(id =>
                                document.getElementById(id)
                            )
                            .filter(Boolean)
                            .map(node =>
                                node.innerText
                            );

                    const result =
                        clean(parts.join(" "));

                    if (result) {
                        return result;
                    }
                }

                // Native label association.
                if (el.labels &&
                    el.labels.length > 0) {

                    const result =
                        clean(
                            Array.from(el.labels)
                                .map(label =>
                                    label.innerText
                                )
                                .join(" ")
                        );

                    if (result) {
                        return result;
                    }
                }

                // Placeholder.
                const placeholder =
                    el.getAttribute(
                        "placeholder"
                    );

                if (placeholder) {
                    return clean(placeholder);
                }

                // Visible element text.
                const text =
                    clean(el.innerText);

                if (text) {
                    return text;
                }

                // Current value.
                return clean(
                    el.value
                );
            }
            """
        )

        return name or ""

    except Exception:
        return ""


async def _observe_select_options(
    select,
) -> list:
    """
    Observe every option in a native <select>.

    The LLM receives both:
    - human-readable label
    - actual option value

    This allows it to choose an option without
    inventing selectors or values.
    """

    options = select.locator("option")

    count = await options.count()

    result = []

    for i in range(count):
        option = options.nth(i)

        try:
            label = (
                await option.inner_text()
            ).strip()

            value = (
                await option.get_attribute(
                    "value"
                )
            )

            disabled = (
                await option.is_disabled()
            )

            selected = await option.evaluate(
                "(el) => el.selected"
            )

            result.append(
                {
                    "index": i,
                    "label": label,
                    "value": value
                    if value is not None
                    else label,
                    "selected": selected,
                    "disabled": disabled,
                }
            )

        except Exception:
            continue

    return result


# async def _observe_data_elements(
#     page: Page,
# ) -> list:
#     """
#     Observe non-interactive data-bearing elements
#     that can be useful for extraction or completion
#     verification.
#     """

#     data_elements = []

#     selectors = [
#         "[data-field]",
#         "[role='alert']",
#         "[role='status']",
#         "[role='heading']",
#     ]

#     for selector in selectors:
#         locator = page.locator(selector)

#         count = await locator.count()

#         for i in range(count):
#             element = locator.nth(i)

#             try:
#                 if not await element.is_visible():
#                     continue

#                 text = (
#                     await element.inner_text()
#                 ).strip()

#                 if not text:
#                     continue

#                 observed_selector = selector

#                 if selector == "[data-field]":
#                     data_field = (
#                         await element.get_attribute(
#                             "data-field"
#                         )
#                     )

#                     if data_field:
#                         observed_selector = (
#                             f"[data-field='{data_field}']"
#                         )

#                 data_elements.append(
#                     {
#                         "selector": observed_selector,
#                         "index": i,
#                         "text": text,
#                         "id": await element.get_attribute(
#                             "id"
#                         ),
#                         "data_field": await element.get_attribute(
#                             "data-field"
#                         ),
#                         "class": await element.get_attribute(
#                             "class"
#                         ),
#                         "role": await element.get_attribute(
#                             "role"
#                         ),
#                     }
#                 )

#             except Exception:
#                 continue

#     return data_elements


from typing import Any
from playwright.async_api import Page


async def _observe_data_elements(
    page: Page,
    *,
    max_text_length: int = 2000,
    include_navigation: bool = False,
) -> list[dict[str, Any]]:
    """
    Observe visible, potentially data-bearing elements on a general HTML page.

    The function tries to identify:
      - Explicit data attributes
      - ARIA/status/alert elements
      - Headings
      - Form controls and labels
      - Tables and table rows/cells
      - Definition lists
      - Semantic content containers
      - Links containing meaningful information

    Returns a list of structured observations.
    """

    observations: list[dict[str, Any]] = []
    seen: set[str] = set()

    selectors = [
        # Explicit application/data attributes
        "[data-field]",
        "[data-value]",
        "[data-testid]",
        "[data-id]",

        # ARIA / accessibility information
        "[role='alert']",
        "[role='status']",
        "[role='heading']",
        "[role='cell']",
        "[role='row']",

        # Semantic content
        "h1, h2, h3, h4, h5, h6",
        "article",
        "main",
        "section",

        # Structured data
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "dt",
        "dd",

        # Lists
        "ul > li",
        "ol > li",

        # Forms / values
        "label",
        "input",
        "textarea",
        "select",
        "option",
        "output",
        "button",

        # Useful metadata/content
        "time",
        "blockquote",
        "figure",
        "figcaption",

        # Links
        "a",
    ]

    for selector in selectors:
        locator = page.locator(selector)
        count = await locator.count()

        for index in range(count):
            element = locator.nth(index)

            try:
                if not await element.is_visible():
                    continue

                # ---------------------------------------------------------
                # Avoid duplicate observations.
                #
                # The same element can match multiple selectors.
                # Element handles are not always ideal as dictionary keys,
                # so create a lightweight DOM identity.
                # ---------------------------------------------------------
                identity = await element.evaluate(
                    """
                    el => {
                        if (el.id) {
                            return `id:${el.id}`;
                        }

                        const parts = [];
                        let node = el;

                        while (node && node.nodeType === 1 && parts.length < 5) {
                            let part = node.tagName.toLowerCase();

                            if (node.classList.length) {
                                part += "." + [...node.classList]
                                    .slice(0, 2)
                                    .join(".");
                            }

                            const parent = node.parentElement;

                            if (parent) {
                                const siblings = [
                                    ...parent.children
                                ];

                                const sameTagIndex =
                                    siblings
                                        .filter(
                                            x =>
                                                x.tagName === node.tagName
                                        )
                                        .indexOf(node);

                                part += `:nth-of-type(${sameTagIndex + 1})`;
                            }

                            parts.unshift(part);
                            node = parent;
                        }

                        return parts.join(" > ");
                    }
                    """
                )

                if identity in seen:
                    continue

                seen.add(identity)

                # ---------------------------------------------------------
                # Extract visible text
                # ---------------------------------------------------------
                text = (
                    await element.inner_text()
                ).strip()

                # Form controls may not have inner_text().
                # In that case, inspect their value.
                value = await element.get_attribute("value")

                if not text and value:
                    text = value.strip()

                # aria-label is often the only useful text on
                # buttons, inputs, icons, etc.
                aria_label = await element.get_attribute("aria-label")

                if not text and aria_label:
                    text = aria_label.strip()

                # title can provide useful semantic information
                title = await element.get_attribute("title")

                if not text and title:
                    text = title.strip()

                if not text:
                    continue

                # ---------------------------------------------------------
                # Ignore very large blocks of text.
                # ---------------------------------------------------------
                if len(text) > max_text_length:
                    text = text[:max_text_length] + "..."

                tag_name = (
                    await element.evaluate(
                        "el => el.tagName.toLowerCase()"
                    )
                )

                role = await element.get_attribute("role")
                element_id = await element.get_attribute("id")
                class_name = await element.get_attribute("class")

                data_field = await element.get_attribute("data-field")
                data_value = await element.get_attribute("data-value")
                data_testid = await element.get_attribute("data-testid")
                name = await element.get_attribute("name")

                href = None
                if tag_name == "a":
                    href = await element.get_attribute("href")

                # ---------------------------------------------------------
                # Determine a more useful element type.
                # ---------------------------------------------------------
                if data_field:
                    element_type = "data_field"
                    reason = "explicit data-field attribute"

                elif role in {"alert", "status"}:
                    element_type = "status"
                    reason = f"ARIA {role} element"

                elif tag_name in {
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                } or role == "heading":
                    element_type = "heading"
                    reason = "heading/content structure"

                elif tag_name in {"th", "td"} or role == "cell":
                    element_type = "table_cell"
                    reason = "structured table data"

                elif tag_name == "tr" or role == "row":
                    element_type = "table_row"
                    reason = "structured table row"

                elif tag_name in {"input", "textarea", "select", "output"}:
                    element_type = "form_value"
                    reason = "form/value element"

                elif tag_name in {"dt", "dd"}:
                    element_type = "definition"
                    reason = "definition-list data"

                elif tag_name == "time":
                    element_type = "time"
                    reason = "time/date element"

                elif tag_name == "a":
                    element_type = "link"
                    reason = "navigational/content link"

                elif tag_name in {"article", "main", "section"}:
                    element_type = "content"
                    reason = "semantic content container"

                else:
                    element_type = "text"
                    reason = "visible text-bearing element"

                # ---------------------------------------------------------
                # Optionally exclude navigation links.
                # ---------------------------------------------------------
                if not include_navigation and tag_name == "a":
                    is_navigation = await element.evaluate(
                        """
                        el => {
                            const parent = el.closest(
                                "nav, header, footer, [role='navigation']"
                            );
                            return !!parent;
                        }
                        """
                    )

                    if is_navigation:
                        continue

                # ---------------------------------------------------------
                # Build a useful selector.
                # ---------------------------------------------------------
                if element_id:
                    observed_selector = f"#{element_id}"

                elif data_field:
                    observed_selector = (
                        f"[data-field='{data_field}']"
                    )

                elif data_testid:
                    observed_selector = (
                        f"[data-testid='{data_testid}']"
                    )

                elif name:
                    observed_selector = (
                        f"{tag_name}[name='{name}']"
                    )

                else:
                    observed_selector = selector

                observations.append(
                    {
                        "selector": observed_selector,
                        "source_selector": selector,
                        "index": index,
                        "element_type": element_type,
                        "reason": reason,
                        "tag": tag_name,
                        "text": text,
                        "value": value,
                        "id": element_id,
                        "name": name,
                        "data_field": data_field,
                        "data_value": data_value,
                        "data_testid": data_testid,
                        "class": class_name,
                        "role": role,
                        "aria_label": aria_label,
                        "title": title,
                        "href": href,
                    }
                )

            except Exception:
                # DOMs can change while being inspected.
                # Ignore one bad element and continue.
                continue

    return observations
