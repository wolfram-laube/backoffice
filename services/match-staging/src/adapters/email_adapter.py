"""Email notification adapter using Gmail API.

Uses lightweight OAuth refresh token flow (same as applications_drafts.py).
No google-auth-oauthlib dependency needed — just requests.

Environment variables:
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader

from src.config import EmailConfig
from src.models import NotificationPayload

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"


class EmailAdapter:
    """Gmail API adapter for email notifications."""

    channel_name = "email"

    def __init__(self, config: EmailConfig):
        self.config = config
        self._access_token: str | None = None
        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )

    @property
    def is_enabled(self) -> bool:
        return (
            self.config.enabled
            and len(self.config.recipients) > 0
            and bool(self.config.client_id)
            and bool(self.config.refresh_token)
        )

    async def _get_access_token(self) -> str:
        """Get OAuth access token via refresh token."""
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                OAUTH_TOKEN_URL,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "refresh_token": self.config.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
            return self._access_token

    async def send(self, payload: NotificationPayload) -> bool:
        """Send HTML email with match summary."""
        try:
            token = await self._get_access_token()

            # Try Jinja2 template, fallback to plain text
            try:
                template = self._jinja.get_template("match_summary.html")
                html_content = template.render(
                    cycle_id=payload.cycle_id,
                    matches_count=payload.matches_count,
                    matches=sorted(
                        payload.matches,
                        key=lambda m: m.overall_score,
                        reverse=True,
                    ),
                    summary=payload.summary,
                    review_url=payload.review_url,
                    timestamp=payload.timestamp.strftime("%d.%m.%Y %H:%M"),
                )
            except Exception as e:
                logger.warning(f"Template render failed, using plain: {e}")
                html_content = None

            # Build subject
            top_match = max(payload.matches, key=lambda m: m.overall_score)
            subject = (
                f"[Blauweiss] {payload.matches_count} neue Job-Matches "
                f"— Top: {top_match.overall_score}% {top_match.title}"
            )

            async with httpx.AsyncClient() as client:
                for recipient in self.config.recipients:
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = subject
                    msg["From"] = "me"
                    msg["To"] = recipient

                    # Plain text fallback
                    msg.attach(MIMEText(payload.summary, "plain", "utf-8"))

                    # HTML version
                    if html_content:
                        msg.attach(MIMEText(html_content, "html", "utf-8"))

                    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

                    resp = await client.post(
                        GMAIL_SEND_URL,
                        headers={"Authorization": f"Bearer {token}"},
                        json={"raw": raw},
                    )
                    resp.raise_for_status()
                    logger.info(f"Email sent to {recipient}")

            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    async def health_check(self) -> bool:
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    GMAIL_PROFILE_URL,
                    headers={"Authorization": f"Bearer {token}"},
                )
                return resp.status_code == 200
        except Exception:
            return False
