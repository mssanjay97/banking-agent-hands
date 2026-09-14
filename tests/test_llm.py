import pytest

from app.agent.llm import ask_llm


@pytest.mark.asyncio
async def test_llm_returns_valid_action():
    goal = "Find member 12345 and retrieve their savings balance."

    observation = {
        "url": "http://127.0.0.1:3000/members",
        "title": "Member Search",
        "text": (
            "Member Search Enter the member ID "
            "to retrieve account information."
        ),
        "interactive_elements": [
            {
                "index": 0,
                "tag": "input",
                "text": "",
                "accessible_name": "Member ID",
                "aria_label": None,
                "id": "member-id",
                "html_name": "member_id",
                "type": "text",
                "placeholder": None,
                "value": "",
                "checked": None,
                "selected": None,
                "disabled": False,
            },
            {
                "index": 1,
                "tag": "button",
                "text": "Search",
                "accessible_name": "Search",
                "aria_label": None,
                "id": None,
                "html_name": None,
                "type": "submit",
                "placeholder": None,
                "value": "",
                "checked": None,
                "selected": None,
                "disabled": False,
            },
        ],
        "data_elements": [],
    }

    action = await ask_llm(
        goal,
        observation,
    )

    assert isinstance(action, dict)
    assert "action" in action
    assert action["action"] in {
        "navigate",
        "fill",
        "click",
        "extract",
    }