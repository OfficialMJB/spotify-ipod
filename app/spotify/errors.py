"""Safe application and upstream error types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AppError(Exception):
    """An expected error that can be returned through the public API."""

    code: str
    message: str
    status_code: int
    recoverable: bool = False
    retry_after: int | None = None

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.retry_after is not None:
            error["retry_after"] = self.retry_after
        return {"error": error}


class SpotifyError(AppError):
    """A normalized Spotify OAuth or Web API failure."""
