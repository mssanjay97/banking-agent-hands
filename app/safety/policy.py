from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class SafetyPolicy:
    """
    Controls which browser actions the automation system may perform.
    """

    allowed_domains: list[str]
    allowed_actions: list[str]
    risky_actions: list[str]

    def check_url(self, url: str) -> None:
        """
        Block navigation outside the configured domain allowlist.
        """

        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            raise ValueError(
                f"Invalid URL: {url}"
            )

        if hostname not in self.allowed_domains:
            raise PermissionError(
                f"Navigation blocked by safety policy: {url}"
            )

    def check_action(self, action: dict) -> None:
        """
        Block actions that are not explicitly allowed.
        """

        action_type = action.get("action")

        if action_type not in self.allowed_actions:
            raise PermissionError(
                f"Action blocked by safety policy: {action_type}"
            )

        if action_type in self.risky_actions:
            raise PermissionError(
                f"Risky action requires human confirmation: {action_type}"
            )