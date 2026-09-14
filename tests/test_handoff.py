import pytest
from playwright.async_api import async_playwright

import app.handoff.controller as controller


@pytest.mark.asyncio
async def test_wait_for_human(monkeypatch, tmp_path):
    completion_checks = 0

    async def fake_sleep(seconds):
        nonlocal completion_checks
        completion_checks += 1

    def fake_create_handoff_request(**kwargs):
        assert kwargs["goal"] == "Test human handoff"
        assert kwargs["step"] == 2
        assert kwargs["reason"] == "Agent is unable to continue."
        assert kwargs["current_url"].endswith("/members")
        return str(tmp_path / "handoff_request.json")

    def fake_is_handoff_complete():
        return completion_checks >= 1

    monkeypatch.setattr(
        controller,
        "create_handoff_request",
        fake_create_handoff_request,
    )

    monkeypatch.setattr(
        controller,
        "is_handoff_complete",
        fake_is_handoff_complete,
    )

    monkeypatch.setattr(
        controller.asyncio,
        "sleep",
        fake_sleep,
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True
        )

        page = await browser.new_page()

        await page.goto(
            "http://127.0.0.1:3000/members"
        )

        await controller.wait_for_human(
            goal="Test human handoff",
            step=2,
            reason="Agent is unable to continue.",
            page=page,
        )

        assert completion_checks >= 1

        await browser.close()