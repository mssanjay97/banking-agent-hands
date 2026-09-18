import asyncio
import json

from openai import OpenAI


client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


MODEL = "qwen3:8b"
LLM_TIMEOUT_SECONDS = 145

import json


def build_prompt(
    goal,
    observation,
    previous_action=None,
    previous_result=None,
):
    observation_json = json.dumps(observation, indent=2)
    previous_action_json = (
        json.dumps(previous_action, indent=2)
        if previous_action
        else "None"
    )
    previous_result_json = (
        json.dumps(previous_result, indent=2)
        if previous_result
        else "None"
    )

    return """
You are a browser automation agent operating a web application.

GOAL:
GOAL

CURRENT BROWSER STATE:
OBSERVATION

PREVIOUS ACTION:
PREVIOUS_ACTION

PREVIOUS ACTION RESULT:
PREVIOUS_RESULT


Your task is to choose exactly ONE next action that makes direct progress toward completing the GOAL.

The GOAL is the only source of truth for what the agent needs to accomplish.


DECISION PROCESS:

1. Determine what the GOAL requires.

2. Determine which requirements of the GOAL have already been completed based on the CURRENT BROWSER STATE and PREVIOUS ACTION RESULT.

3. Determine what requirement is still incomplete.

4. Choose exactly ONE action that directly advances the incomplete requirement.

5. After every action, expect the browser state to change. Re-evaluate the entire GOAL using the new state before choosing the next action.


IMPORTANT:

- Do NOT choose an action merely because a control is visible.
- Do NOT click unrelated buttons, links, menus, tabs, or controls.
- Do NOT navigate to unrelated pages.
- Do NOT explore the application unnecessarily.
- Prefer the shortest valid sequence of actions that completes the GOAL.
- Never repeat an action that already succeeded unless the new browser state clearly requires it.
- Use only elements, selectors, URLs, values, and options present in the CURRENT BROWSER STATE or explicitly provided by the GOAL.
- Never invent an element, selector, URL, option, or value.
- Prefer accessible role and name when available.
- If an element has both a role/name and selector, prefer role/name for interaction.
- If the requested information is already visible, use extract rather than clicking unrelated controls.
- If information must first be obtained by an action such as submitting a form or navigating, perform that required action first.
- If the GOAL contains multiple operations, complete ALL required operations.
- Extracting information does NOT automatically mean the workflow is finished.
- After an extract action, inspect the GOAL again and determine whether additional requirements remain.
- Do NOT use done immediately after extract unless the entire GOAL has been completed.
- Use done ONLY when every requirement in the GOAL is complete and there is observable evidence that the workflow is finished.


ACTION PRIORITY:

Use this priority when deciding what to do next:

A. Is the entire GOAL already complete and is there observable completion evidence?
   → Use done.

B. Is information explicitly requested by the GOAL currently visible in the browser?
   → Use extract on the relevant visible information.

C. Is a required input for an incomplete part of the GOAL missing?
   → Use fill, select, check, or another appropriate input action.

D. Is a required submission, button, link, or navigation action needed to make progress toward the GOAL?
   → Use click or navigate.

E. Otherwise:
   → Choose the single action that makes the most direct progress toward the incomplete part of the GOAL.

Never select an action simply because it is available.


FORM RULES:

- Before changing a form field, inspect its current state.
- If the required value is already correct, do not change it.
- For fill, use the exact concrete value required by the GOAL.
- For select, use only an option value that is actually observed.
- For check, use it only when the required state is unchecked.
- For uncheck, use it only when the required state is checked.
- Do not modify unrelated fields.
- Do not submit a form until the required information for the current GOAL step has been provided.


EXTRACTION RULES:

- Use extract when the GOAL requires retrieving, reading, obtaining, returning, reporting, or extracting information from the browser.
- Extract only information that is currently visible.
- The extraction target must correspond to the requested information.
- Do not invent an extraction target.
- If multiple similar elements exist, use the element whose surrounding context identifies the requested information.
- Do not assume that the first matching element is the correct element.
- If the requested information is visible but the target is ambiguous, choose a more specific observed target.
- Extracting one value does not mean the GOAL is complete.
- After extraction, continue evaluating the remaining GOAL requirements.


CLICK RULES:

- Click only when the click directly advances an incomplete requirement of the GOAL.
- Do not click unrelated controls.
- Do not click a visible button/link just because it looks useful.
- Before clicking, identify why the click is required by the GOAL.
- The target must be an observed element.
- For click, value MUST be null.


NAVIGATION RULES:

- Navigate only when navigation is required to complete the GOAL.
- Never navigate to an invented URL.
- Use only an observed or explicitly provided URL.
- Do not navigate simply to explore the application.


DISCOVERY RULES:

- This is the discovery phase.
- Use the exact concrete values from the GOAL.
- Do NOT replace concrete values with placeholders during discovery.
- Parameterization is performed separately after successful discovery.
- Preserve exact values when performing actions.
- The recorded workflow must represent the actual successful sequence used to complete the GOAL.


COMPLETION RULES:

Use done only when:

1. Every requirement in the GOAL has been completed.
2. The browser is in the expected final state.
3. There is observable evidence supporting completion.
4. No additional operation required by the GOAL remains.

Do NOT use done merely because:

- one action succeeded,
- a page loaded,
- a form was submitted,
- requested information became visible,
- an extract succeeded,
- or the current page looks complete.

If any part of the GOAL remains incomplete, continue with another action.


ACTION SCHEMAS:

Return exactly ONE JSON object using one of these actions.

Navigate:
{
  "action": "navigate",
  "target": {
    "role": null,
    "name": null,
    "id": null,
    "selector": "OBSERVED_SELECTOR"
  },
  "value": "OBSERVED_OR_EXPLICIT_URL"
}

Fill:
{
  "action": "fill",
  "target": {
    "role": "input",
    "name": "OBSERVED_NAME",
    "id": "OBSERVED_ID",
    "selector": "OBSERVED_SELECTOR"
  },
  "value": "EXACT_REQUIRED_VALUE"
}

Clear:
{
  "action": "clear",
  "target": {
    "role": "input",
    "name": "OBSERVED_NAME",
    "id": "OBSERVED_ID",
    "selector": "OBSERVED_SELECTOR"
  },
  "value": null
}

Select:
{
  "action": "select",
  "target": {
    "role": "combobox",
    "name": "OBSERVED_NAME",
    "id": "OBSERVED_ID",
    "selector": "OBSERVED_SELECTOR"
  },
  "value": "OBSERVED_OPTION_VALUE"
}

Check:
{
  "action": "check",
  "target": {
    "role": "checkbox",
    "name": "OBSERVED_NAME",
    "id": "OBSERVED_ID",
    "selector": "OBSERVED_SELECTOR"
  },
  "value": null
}

Uncheck:
{
  "action": "uncheck",
  "target": {
    "role": "checkbox",
    "name": "OBSERVED_NAME",
    "id": "OBSERVED_ID",
    "selector": "OBSERVED_SELECTOR"
  },
  "value": null
}

Click:
{
  "action": "click",
  "target": {
    "role": "button",
    "name": "OBSERVED_NAME",
    "id": "OBSERVED_ID",
    "selector": "OBSERVED_SELECTOR"
  },
  "value": null
}

Extract:
{
  "action": "extract",
  "target": {
    "role": "OBSERVED_ROLE",
    "name": "OBSERVED_NAME",
    "id": "OBSERVED_ID",
    "selector": "OBSERVED_SELECTOR"
  },
  "value": null,
  "output": "DESCRIPTIVE_OUTPUT_NAME"
}

Done:
{
  "action": "done",
  "target": {
    "role": "OBSERVED_ROLE",
    "name": "OBSERVED_NAME",
    "id": "OBSERVED_ID",
    "selector": "OBSERVED_SELECTOR"
  },
  "value": null
}


TARGET RULES:

- target fields must describe an element observed in the CURRENT BROWSER STATE.
- Do not invent target names.
- Do not invent selectors.
- Do not invent IDs.
- Do not use a generic selector when a more specific observed target is available.
- If multiple elements match a selector, choose a target that uniquely identifies the intended element.
- For extraction, the target must identify the requested information rather than simply selecting the first matching element.
- For click, clear, check, uncheck, extract, and done, value MUST be null.
- For fill, select, and navigate, value must contain the required value.


IMPORTANT MULTI-STEP RULE:

The GOAL may require several different operations.

For example, a GOAL may require the agent to:

- enter information,
- submit it,
- retrieve information,
- perform another operation,
- verify the result,
- and then finish.

Do not assume that any particular action is the final action.

After EVERY action:

1. Inspect the new browser state.
2. Re-read the GOAL.
3. Identify what remains incomplete.
4. Choose the next action that directly advances the remaining requirement.

The agent must reason about the COMPLETE GOAL, not just the current page or previous action.


OUTPUT FORMAT:

Return ONLY valid JSON.

Return exactly ONE action.

Do not include markdown.

Do not include explanations.

Do not include reasoning.

Do not include multiple actions.

Do not include comments.
""".replace(
        "GOAL", goal
    ).replace(
        "OBSERVATION", observation_json
    ).replace(
        "PREVIOUS_ACTION", previous_action_json
    ).replace(
        "PREVIOUS_RESULT", previous_result_json
    )

def _ask_llm_sync(
    goal: str,
    observation: dict,
    previous_action: dict | None = None,
    previous_result: dict | None = None,
) -> dict:

    prompt = build_prompt(
        goal=goal,
        observation=observation,
        previous_action=previous_action,
        previous_result=previous_result,
    )
    
    """
You are a computer-use agent operating a web application.

Goal:
{goal}

Current browser state:
{json.dumps(observation, indent=2)}

Previous action:
{json.dumps(previous_action, indent=2) if previous_action else "None"}

Previous action result:
{json.dumps(previous_result, indent=2) if previous_result else "None"}

Your task is to complete the user's goal by inspecting the current
browser state and choosing exactly ONE next browser action.

You are operating the browser through structured actions.

Available actions:

1. navigate

{{
  "action": "navigate",
  "target": {{
    "role": null,
    "name": null,
    "id": null,
    "selector": null
  }},
  "value": "URL"
}}

2. fill

{{
  "action": "fill",
  "target": {{
    "role": "...",
    "name": "..."
  }},
  "value": "..."
}}

Use fill for:
- text
- email
- password
- number
- telephone
- URL
- search
- date
- time
- datetime-local
- textarea
- contenteditable
- other value-bearing form controls

3. clear

{{
  "action": "clear",
  "target": {{
    "role": "...",
    "name": "..."
  }},
  "value": null
}}

Use clear when an existing field value needs to be removed
before entering a different value.

4. select

{{
  "action": "select",
  "target": {{
    "role": "combobox",
    "name": "..."
  }},
  "value": "..."
}}

Use select only for native dropdown/select controls.

The current browser observation contains an "options" list for
select controls.

Choose the option's actual "value" from that list.

Do not invent an option value.

5. check

{{
  "action": "check",
  "target": {{
    "role": "checkbox",
    "name": "..."
  }},
  "value": null
}}

Use check when a checkbox or checkable control must be enabled.

6. uncheck

{{
  "action": "uncheck",
  "target": {{
    "role": "checkbox",
    "name": "..."
  }},
  "value": null
}}

Use uncheck when a checkbox must be disabled.

7. click

{{
  "action": "click",
  "target": {{
    "role": "...",
    "name": "..."
  }},
  "value": null
}}

Use click for buttons, links, and other clickable controls.

8. extract

{{
  "action": "extract",
  "target": {{
    "role": null,
    "name": null,
    "id": null,
    "selector": "..."
  }},
  "value": null
}}

Use extract when the goal requires reading information from
the current page.

9. done

{{
  "action": "done",
  "target": {{
    "role": "...",
    "name": "..."
  }},
  "value": null
}}

Use done ONLY when the user's goal has actually been completed.

The target must identify observable evidence on the current page
that demonstrates completion.

For example, if the current page visibly contains a success
status saying that an operation completed, the done target can
identify that status.

Do not use done merely because all expected actions have been
performed.

The completion target must be something currently observable
in the browser state.

- Inspect the current browser state before choosing an action.
- Do NOT repeat an action that has already succeeded.
- If an input already contains the required value, do NOT fill it again.
- After filling the required input, look for the button needed to continue.
- If the required button is visible, click it.
- Only extract a value after navigating to the page where that value
  is actually visible.
- Do not invent elements that are not present in the observation.
- For buttons and inputs, use "accessible_name" as the target "name".
- Do NOT use "html_name" as the target name.
- Prefer accessible roles and names for buttons and inputs.
- Use stable selectors for extraction.

- Return exactly ONE action.
- Return JSON only.
- Never invent an element.
- Use only elements present in the current browser state.
- Prefer accessible role and name for interaction.
- Prefer stable CSS selectors for extraction.
- If a required field is empty, fill it.
- If a required field already contains the requested value, do not fill it again.
- If the previous step completed a form entry and a visible button can continue the workflow, click that button.
- After navigation or clicking, wait for the next observation before extracting.
- If the requested information is visible, extract it.
- Do not repeat a successful action.
- Do not explain your reasoning.

    
IMPORTANT RULES:

- Inspect the current browser state before choosing an action.
- Choose exactly ONE action.
- Never invent an element.
- Use only controls present in the current observation.
- Prefer accessible role + accessible name for interaction.
- Do not use html_name as the accessible name.
- Prefer stable IDs when an accessible target is unavailable.
- Prefer stable CSS selectors for extraction.
- Do not construct selectors such as:
  a[accessible_name='...']
  input[accessible_name='...']
  button[accessible_name='...']
  These are not valid CSS selectors.
- For native select controls, use the observed role "combobox".
- Before selecting, inspect the observed options.
- Use the actual option value from the observation.
- Do not select an option that is not present.
- For checkboxes, inspect the current checked state before deciding
  whether to check or uncheck.
- For inputs, inspect the current value before deciding whether
  to fill or clear.
- If the current value already equals the required value, do not
  fill it again.
- Do not repeat an action that already succeeded.
- After filling a required field, continue to the next required
  field or the appropriate visible action.
- After selecting a required option, continue to the next required
  field or the appropriate visible action.
- Do not click a submit button while required fields still contain
  incorrect or missing values.
- Do not assume that the browser automatically selected the
  requested option.
- After clicking or navigating, wait for the next observation before
  deciding what to do.
- Only extract information after navigating to a page where that
  information is visible.
- Only use done when observable evidence of completion exists.
- Do not use extract as a substitute for done.
- Do not terminate merely because an action succeeded.
- Do not repeat the workflow after the goal has been completed.
- Do not explain your reasoning.
- Return JSON only.
- Preserve the exact meaning of values specified in the goal.
- During discovery, execute actions using the exact concrete values present in the goal.
- Do not replace concrete values with placeholders.
- Parameterization is performed by the discovery recorder after successful execution.
- Never shorten, round, approximate, reinterpret, or change a value.
- If the goal asks to retrieve, read, get, return, report, extract, or obtain a value from the page, you must use the extract action on the relevant visible data element before using done.
- Do not use done merely because the requested information is visible.
- Use done only after the requested information has actually been extracted.

FORM COMPLETION RULES:
- Before clicking a submit/create/save/continue button, inspect the current page for form controls relevant to the goal.
- Do not submit a form if a required value from the goal has not yet been entered or selected.
- If the goal specifies a value for a textbox/input, use fill before submitting.
- If the goal specifies a choice for a select/combobox, use select before submitting.
- Use the currently observed value to determine whether a field is already correctly populated.
- A default value is not evidence that the user's requested value has been entered.
- Only click the submit/create/save/continue control after all required goal values are satisfied.

For click:
- Click a control only when it is the next action needed to advance the goal.
- If the page contains an incomplete form, do not click its submit button prematurely.

For select:
- Use the actual option value from the observed options.
- Never invent an option value.


    """

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "computer_action",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "navigate",
                                "fill",
                                "clear",
                                "select",
                                "check",
                                "uncheck",
                                "click",
                                "extract",
                                "done",
                            ],
                        },
                        "target": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": [
                                        "string",
                                        "null",
                                    ]
                                },
                                "name": {
                                    "type": [
                                        "string",
                                        "null",
                                    ]
                                },
                                "id": {
                                    "type": [
                                        "string",
                                        "null",
                                    ]
                                },
                                "selector": {
                                    "type": [
                                        "string",
                                        "null",
                                    ]
                                },
                            },
                            "required": [
                                "role",
                                "name",
                                "id",
                                "selector",
                            ],
                            "additionalProperties": False,
                        },
                        "value": {
                            "type": [
                                "string",
                                "null",
                            ]
                        },
                    },
                    "required": [
                        "action",
                        "target",
                        "value",
                    ],
                    "additionalProperties": False,
                },
            },
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "LLM returned an empty response"
        )

    return json.loads(content)


async def ask_llm(
    goal: str,
    observation: dict,
    previous_action: dict | None = None,
    previous_result: dict | None = None,
) -> dict:

    return await asyncio.wait_for(
        asyncio.to_thread(
            _ask_llm_sync,
            goal,
            observation,
            previous_action,
            previous_result,
        ),
        timeout=LLM_TIMEOUT_SECONDS,
    )


def _extract_parameters_sync(goal: str) -> dict:
    prompt = f"""
You are analyzing a user's automation goal.

Identify every value in the goal that should be supplied as a runtime
parameter when this automation is replayed.

Rules:
- Identify values that can reasonably change between executions.
- Do NOT invent values.
- Do NOT identify UI labels, button names, field names, or generic words.
- Preserve values exactly as written.
- Give each parameter a generic semantic snake_case name.
- Do not use names tied to this specific application.
- If a value represents an identifier, use an appropriate *_id or *_number name.
- If it represents money, use amount.
- If it represents a date, use date.
- If it represents a person's name, use a suitable name such as person_name.
- If no runtime parameters exist, return an empty list.

Goal:
{goal}

Return JSON only in this format:

{{
  "parameters": [
    {{
      "name": "parameter_name",
      "value": "exact value from goal",
      "type": "string"
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You identify runtime parameters in automation goals."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "parameter_extraction",
                "schema": {
                    "type": "object",
                    "properties": {
                        "parameters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "string"},
                                    "type": {
                                        "type": "string",
                                        "enum": [
                                            "string",
                                            "number",
                                            "boolean",
                                            "date"
                                        ]
                                    }
                                },
                                "required": [
                                    "name",
                                    "value",
                                    "type"
                                ],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["parameters"],
                    "additionalProperties": False
                }
            }
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )

    return json.loads(response.choices[0].message.content)


async def extract_parameters(goal: str) -> dict:
    return await asyncio.wait_for(
        asyncio.to_thread(_extract_parameters_sync, goal),
        timeout=LLM_TIMEOUT_SECONDS
    )