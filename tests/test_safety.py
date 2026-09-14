from app.safety.policy import SafetyPolicy


policy = SafetyPolicy(
    allowed_domains=["127.0.0.1"],
    allowed_actions=[
        "navigate",
        "fill",
        "click",
        "extract",
        "transfer_money",
    ],
    risky_actions=[
        "transfer_money",
    ],
)


def test_allowed_url():
    policy.check_url(
        "http://127.0.0.1:3000/members"
    )


def test_external_url_is_blocked():
    try:
        policy.check_url(
            "https://example.com"
        )
    except PermissionError:
        return

    raise AssertionError("External URL was not blocked")


def test_unsupported_action_is_blocked():
    try:
        policy.check_action(
            {
                "action": "delete"
            }
        )
    except PermissionError:
        return

    raise AssertionError("Unsupported action was not blocked")


def test_risky_action_is_blocked():
    try:
        policy.check_action(
            {
                "action": "transfer_money"
            }
        )
    except PermissionError:
        return

    raise AssertionError("Risky action was not blocked")