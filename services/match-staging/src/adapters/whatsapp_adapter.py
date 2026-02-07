"""WhatsApp notification adapter via Twilio API.

Sends concise text messages with match summaries.
Uses Twilio WhatsApp Business API (or Sandbox for testing).
"""

import logging

import httpx

from src.config import WhatsAppConfig
from src.models import NotificationPayload

logger = logging.getLogger(__name__)

TWILIO_API = "https://api.twilio.com/2010-04-01"


class WhatsAppAdapter:
    """Twilio WhatsApp adapter."""

    channel_name = "whatsapp"

    def __init__(self, config: WhatsAppConfig):
        self.config = config

    @property
    def is_enabled(self) -> bool:
        return (
            self.config.enabled
            and bool(self.config.account_sid)
            and bool(self.config.auth_token)
            and bool(self.config.from_number)
        )

    async def send(self, payload: NotificationPayload) -> bool:
        """Send WhatsApp message via Twilio."""
        try:
            message = self._build_message(payload)
            url = (
                f"{TWILIO_API}/Accounts/{self.config.account_sid}"
                f"/Messages.json"
            )

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    auth=(self.config.account_sid, self.config.auth_token),
                    data={
                        "From": f"whatsapp:{self.config.from_number}",
                        "To": f"whatsapp:{self.config.to_number}",
                        "Body": message,
                    },
                )
                data = resp.json()

                if resp.status_code in (200, 201):
                    logger.info(
                        f"WhatsApp sent, SID: {data.get('sid', 'unknown')}"
                    )
                    return True
                else:
                    logger.error(
                        f"WhatsApp failed: {data.get('message', resp.text)}"
                    )
                    return False

        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return False

    async def health_check(self) -> bool:
        """Verify Twilio credentials."""
        if not self.is_enabled:
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{TWILIO_API}/Accounts/{self.config.account_sid}.json",
                    auth=(self.config.account_sid, self.config.auth_token),
                )
                return resp.status_code == 200
        except Exception:
            return False

    def _build_message(self, payload: NotificationPayload) -> str:
        """Build concise WhatsApp message (< 1600 chars)."""
        lines = [f"🎯 *{payload.matches_count} neue Job-Matches*\n"]

        for match in sorted(
            payload.matches, key=lambda m: m.overall_score, reverse=True
        )[:5]:  # Cap at 5 for message length
            lines.append(
                f"{match.score_emoji} {match.overall_score}% {match.title} "
                f"({match.provider})"
            )

        if payload.matches_count > 5:
            lines.append(f"... +{payload.matches_count - 5} weitere")

        lines.extend(
            [
                "",
                f"👉 Review: {payload.review_url}",
            ]
        )

        return "\n".join(lines)
