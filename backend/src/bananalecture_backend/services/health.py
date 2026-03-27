# ruff: noqa: D107

from bananalecture_backend.core.config import Settings


class HealthService:
    """Service to report application health."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_status(self) -> dict[str, str]:
        """Return status payload."""
        return {"status": "ok", "version": self.settings.APP.VERSION}
