"""Slack notification adapter using Incoming Webhooks.

Sends rich Block Kit messages with match summaries.
No Slack SDK dependency — just a webhook POST via httpx.
"""

import json
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

import httpx

from src.config import SlackConfig
from src.models import NotificationPayload

logger = logging.getLogger(__name__)
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class SlackAdapter:
    """Slack Incoming Webhook adapter."""

    channel_name = "slack"

    def __init__(self, config: SlackConfig):
        self.config = config

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled and bool(self.config.webhook_url)

    async def send(self, payload: NotificationPayload) -> bool:
        """Send Slack Block Kit message via webhook."""
        try:
            blocks = self._build_blocks(payload)
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.config.webhook_url,
                    json={"blocks": blocks, "text": payload.summary},
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code == 200 and resp.text == "ok":
                    logger.info("Slack notification sent")
                    return True
                else:
                    logger.error(f"Slack webhook returned: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            return False

    async def health_check(self) -> bool:
        """Slack webhooks don't have a health endpoint — verify URL is set."""
        return self.is_enabled

    def _build_blocks(self, payload: NotificationPayload) -> list[dict]:
        """Build Slack Block Kit blocks for rich formatting."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎯 {payload.matches_count} neue Job-Matches",
                    "emoji": True,
                },
            },
            {"type": "divider"},
        ]

        for match in sorted(
            payload.matches, key=lambda m: m.overall_score, reverse=True
        ):
            remote_info = (
                f" ({match.remote_percentage}% Remote)"
                if match.remote_percentage
                else ""
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{match.score_emoji} *{match.overall_score}%* — "
                            f"{match.title}\n"
                            f"_{match.provider}_ · {match.location}{remote_info}\n"
                            f"Start: {match.start_date} · Dauer: {match.duration} · "
                            f"{match.rate_eur} EUR/h"
                        ),
                    },
                }
            )

        blocks.extend(
            [
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "👉 Review in GitLab",
                                "emoji": True,
                            },
                            "url": payload.review_url,
                            "style": "primary",
                        }
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": (
                                f"Cycle: `{payload.cycle_id}` · "
                                f"{payload.timestamp.strftime('%d.%m.%Y %H:%M')} UTC"
                            ),
                        }
                    ],
                },
            ]
        )

        return blocks
