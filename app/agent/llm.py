
import asyncio
import json

from openai import OpenAI


client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

MODEL = "qwen3:4b"
LLM_TIMEOUT_SECONDS = 145


def _ask_llm_sync(
    goal: str,
    observation: dict,
) -> dict:


    prompt = f"""

You are a computer-use agent operating a banking web application.

Goal:
{goal}

Current browser state:
{json.dumps(observation, indent=2)}

Choose the next single action needed to accomplish the goal.

Your job is to complete the user's goal by inspecting the current browser
state and choosing the NEXT browser action.

Return ONLY valid JSON.

Available actions:

navigate:
{{"action": "navigate", "target": "URL"}}

fill:
{{"action": "fill", "target": {{"role": "...", "name": "..."}}, "value": "..."}}

click:
{{"action": "click", "target": {{"role": "...", "name": "..."}}}}

extract:
{{"action": "extract", "target": {{"selector": "..."}}}}

Choose exactly ONE action.

IMPORTANT DECISION RULES:

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
                            "click",
                            "extract",
                        ],
                    },
                    "target": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": ["string", "null"],
                            },
                            "name": {
                                "type": ["string", "null"],
                            },
                            "id": {
                                "type": ["string", "null"],
                            },
                            "selector": {
                                "type": ["string", "null"],
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
                        "type": ["string", "null"],
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

    return json.loads(content)


async def ask_llm(
    goal: str,
    observation: dict,
) -> dict:
    """
    Run the blocking LLM client without blocking
    the browser event loop.

    A timeout prevents a stalled local model from
    freezing the entire agent.
    """

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                _ask_llm_sync,
                goal,
                observation,
            ),
            timeout=LLM_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        raise TimeoutError(
            f"LLM decision timed out after "
            f"{LLM_TIMEOUT_SECONDS} seconds."
        )