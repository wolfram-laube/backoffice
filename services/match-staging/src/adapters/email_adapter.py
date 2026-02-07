"""Email notification adapter using Gmail API.

Uses existing credentials.json OAuth flow from backoffice infrastructure.
Sends HTML-formatted match summaries.
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.config import EmailConfig
from src.models import NotificationPayload

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class EmailAdapter:
    """Gmail API adapter for email notifications."""

    channel_name = "email"

    def __init__(self, config: EmailConfig, credentials_path: str = "credentials.json"):
        self.config = config
        self.credentials_path = credentials_path
        self._service = None
        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled and len(self.config.recipients) > 0

    async def _get_service(self):
        """Lazy-init Gmail API service."""
        if self._service:
            return self._service

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
            creds = None
            token_path = Path("token.json")

            if token_path.exists():
                creds = Credentials.from_authorized_user_file(
                    str(token_path), SCOPES
                )

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                token_path.write_text(creds.to_json())

            self._service = build("gmail", "v1", credentials=creds)
            return self._service
        except Exception as e:
            logger.error(f"Gmail API init failed: {e}")
            raise

    async def send(self, payload: NotificationPayload) -> bool:
        """Send HTML email with match summary."""
        try:
            service = await self._get_service()
            template = self._jinja.get_template(f"{self.config.template}.html")

            # Render HTML
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

            # Build subject
            top_match = max(payload.matches, key=lambda m: m.overall_score)
            subject = (
                f"[Blauweiss] {payload.matches_count} neue Job-Matches "
                f"— Top: {top_match.overall_score}% {top_match.title}"
            )

            # Send to all recipients
            for recipient in self.config.recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = "me"
                msg["To"] = recipient
                msg.attach(MIMEText(payload.summary, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
                service.users().messages().send(
                    userId="me", body={"raw": raw}
                ).execute()

                logger.info(f"Email sent to {recipient}")

            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    async def health_check(self) -> bool:
        try:
            service = await self._get_service()
            service.users().getProfile(userId="me").execute()
            return True
        except Exception:
            return False
