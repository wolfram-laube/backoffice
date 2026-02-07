"""Base adapter protocol for notification channels."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from src.models import NotificationPayload


@runtime_checkable
class NotificationAdapter(Protocol):
    """Protocol for notification channel adapters."""

    @property
    def channel_name(self) -> str:
        """Human-readable channel name."""
        ...

    @property
    def is_enabled(self) -> bool:
        """Whether this channel is configured and enabled."""
        ...

    async def send(self, payload: NotificationPayload) -> bool:
        """Send notification. Returns True on success."""
        ...

    async def health_check(self) -> bool:
        """Verify channel connectivity. Returns True if healthy."""
        ...
