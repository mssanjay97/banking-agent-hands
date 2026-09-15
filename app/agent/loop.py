import asyncio

from playwright.async_api import async_playwright

from app.agent.browser import observe_page
from app.agent.actions import execute_action
from app.agent.llm import ask_llm
from app.artifacts.discovery_recorder import DiscoveryRecorder
from app.handoff.controller import wait_for_human

from app.artifacts.builder import build_artifact

START_URL = "http://127.0.0.1:3000/members"


async def run_agent(
    goal: str,
    start_url: str,
    max_steps: int = 10,
):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=False
        )

        page = await browser.new_page()

        await page.goto(start_url)

        recorder = DiscoveryRecorder(
            start_url=start_url
        )


        for step in range(1, max_steps + 1):
            print(f"\n========== STEP {step} ==========")

            observation = await observe_page(page)
            print(observation)
            print("URL:", observation["url"])
            print("TITLE:", observation["title"])

            try:
                action = await ask_llm(
                    goal=goal,
                    observation=observation,
                )

                print("LLM ACTION:")
                print(action)

                result = await execute_action(
                    page,
                    action,
                )

                print("ACTION RESULT:")
                print(result)

                recorder.record(action)

            except Exception as error:
                print("\n========== AGENT STUCK ==========")
                print("Reason:", str(error))

                await wait_for_human(
                    goal=goal,
                    step=step,
                    reason=str(error),
                    page=page,
                    observation=observation,
                )

                print("Human intervention completed.")
                print("Re-observing the same browser session...")

                continue

            if action["action"] == "extract":
                print("\n========== GOAL COMPLETE ==========")
                print("OUTPUT:", result["value"])

                discovery_path = recorder.save()

                print("DISCOVERY ACTIONS SAVED:")
                print(discovery_path)

                artifact_path = build_artifact()

                print("CAPABILITY ARTIFACT SAVED:")
                print(artifact_path)

                break

        else:
            print("\n========== AGENT STOPPED ==========")
            print("Maximum number of steps reached.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(
        run_agent(
            goal="Find member 12345 and retrieve their savings balance.",
            start_url="http://127.0.0.1:3000/members",
        )
    )