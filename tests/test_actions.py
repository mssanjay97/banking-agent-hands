import pytest
from playwright.async_api import async_playwright

from app.agent.actions import execute_action


@pytest.mark.asyncio
async def test_execute_actions():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        await page.goto(
            "http://127.0.0.1:3000/members"
        )

        # Fill member ID.
        result = await execute_action(
            page,
            {
                "action": "fill",
                "target": {
                    "role": "textbox",
                    "name": "Member ID",
                },
                "value": "12345",
            },
        )

        assert result["status"] == "success"

        # Click Search.
        result = await execute_action(
            page,
            {
                "action": "click",
                "target": {
                    "role": "button",
                    "name": "Search",
                },
            },
        )

        assert result["status"] == "success"

        # Extract savings balance.
        result = await execute_action(
            page,
            {
                "action": "extract",
                "target": {
                    "selector": '[data-field="savings-balance"]',
                },
            },
        )

        assert result["status"] == "success"
        assert result["value"] == "$12,840.50"

        await browser.close()