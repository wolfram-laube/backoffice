"""Notification dispatcher — orchestrates multi-channel delivery.

Handles:
- Channel discovery and initialization
- Quiet hours enforcement
- Batch vs. per-match dispatch
- Error isolation (one channel failure doesn't block others)
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from src.config import ServiceConfig
from src.adapters import NotificationAdapter
from src.adapters.email_adapter import EmailAdapter
from src.adapters.gitlab_adapter import GitLabAdapter
from src.adapters.slack_adapter import SlackAdapter
from src.adapters.whatsapp_adapter import WhatsAppAdapter
from src.models import NotificationPayload

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Orchestrates notification delivery across all configured channels."""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.adapters: list[NotificationAdapter] = self._init_adapters()

    def _init_adapters(self) -> list[NotificationAdapter]:
        """Initialize all configured and enabled adapters."""
        channels = self.config.notification.channels
        adapters: list[NotificationAdapter] = []

        # GitLab ToDo (also handles issue creation)
        gitlab = GitLabAdapter(self.config.gitlab, channels.gitlab_todo)
        if gitlab.is_enabled:
            adapters.append(gitlab)

        # Email
        email = EmailAdapter(channels.email)
        if email.is_enabled:
            adapters.append(email)

        # Slack
        slack = SlackAdapter(channels.slack)
        if slack.is_enabled:
            adapters.append(slack)

        # WhatsApp
        whatsapp = WhatsAppAdapter(channels.whatsapp)
        if whatsapp.is_enabled:
            adapters.append(whatsapp)

        logger.info(
            f"Initialized {len(adapters)} notification channels: "
            f"{[a.channel_name for a in adapters]}"
        )
        return adapters

    def _is_quiet_hours(self) -> bool:
        """Check if we're in quiet hours (no notifications)."""
        prefs = self.config.notification.preferences
        qh = prefs.quiet_hours
        try:
            tz = ZoneInfo(qh.timezone)
        except Exception:
            tz = ZoneInfo("Europe/Vienna")

        now = datetime.now(tz).time()
        start = time.fromisoformat(qh.start)
        end = time.fromisoformat(qh.end)

        # Handle overnight quiet hours (e.g., 22:00 - 07:00)
        if start > end:
            return now >= start or now <= end
        return start <= now <= end

    async def dispatch(
        self,
        payload: NotificationPayload,
        force: bool = False,
    ) -> dict[str, bool]:
        """Send notifications to all enabled channels.

        Args:
            payload: The notification content
            force: If True, ignore quiet hours

        Returns:
            Dict mapping channel_name -> success boolean
        """
        if not force and self._is_quiet_hours():
            logger.info("Quiet hours active — notifications deferred")
            return {a.channel_name: False for a in self.adapters}

        if not self.adapters:
            logger.warning("No notification channels configured!")
            return {}

        # Fan-out: send to all channels concurrently, isolate failures
        results = {}

        async def _send_safe(adapter: NotificationAdapter) -> tuple[str, bool]:
            try:
                success = await adapter.send(payload)
                return adapter.channel_name, success
            except Exception as e:
                logger.error(
                    f"Channel {adapter.channel_name} failed: {e}",
                    exc_info=True,
                )
                return adapter.channel_name, False

        tasks = [_send_safe(adapter) for adapter in self.adapters]
        for coro in asyncio.as_completed(tasks):
            name, success = await coro
            results[name] = success
            if success:
                logger.info(f"✅ {name}: sent")
            else:
                logger.warning(f"❌ {name}: failed")

        return results

    async def health_check(self) -> dict[str, bool]:
        """Check health of all configured channels."""
        results = {}
        for adapter in self.adapters:
            try:
                healthy = await adapter.health_check()
                results[adapter.channel_name] = healthy
            except Exception:
                results[adapter.channel_name] = False
        return results

    @property
    def enabled_channels(self) -> list[str]:
        return [a.channel_name for a in self.adapters]
