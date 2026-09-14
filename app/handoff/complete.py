from app.handoff.manager import mark_handoff_complete
from app.handoff.actions import record_human_action


if __name__ == "__main__":
    record_human_action(
        action="manual_browser_intervention",
        description=(
            "Human operator completed the required manual "
            "browser interaction before resuming automation."
        ),
    )

    mark_handoff_complete()

    print("Human handoff marked as complete.")