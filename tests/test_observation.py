import pytest
from playwright.async_api import async_playwright

from app.agent.browser import observe_page


@pytest.mark.asyncio
async def test_observe_page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        await page.goto(
            "http://127.0.0.1:3000/members"
        )

        await page.get_by_role(
            "textbox",
            name="Member ID",
        ).fill("12345")

        await page.get_by_role(
            "button",
            name="Search",
        ).click()

        observation = await observe_page(page)

        assert observation["url"].endswith(
            "/members/search?member_id=12345"
        )

        assert "Member Details" in observation["text"]

        assert any(
            element.get("data_field") == "savings-balance"
            for element in observation["data_elements"]
        )

        assert any(
            element.get("text") == "$12,840.50"
            for element in observation["data_elements"]
        )

        await browser.close()