"""
Gmail API Client
================
Handles OAuth authentication and draft creation.
"""

import os
import base64
import mimetypes
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List

import requests


class GmailClient:
    """Gmail API client using OAuth refresh tokens."""
    
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        """
        Initialize Gmail client.
        
        Credentials can be passed directly or loaded from environment:
        - GMAIL_CLIENT_ID
        - GMAIL_CLIENT_SECRET
        - GMAIL_REFRESH_TOKEN
        """
        self.client_id = client_id or os.environ.get("GMAIL_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("GMAIL_CLIENT_SECRET")
        self.refresh_token = refresh_token or os.environ.get("GMAIL_REFRESH_TOKEN")
        self._access_token: Optional[str] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if all credentials are available."""
        return all([self.client_id, self.client_secret, self.refresh_token])
    
    def get_access_token(self) -> str:
        """Get OAuth access token from refresh token."""
        if not self.is_configured:
            raise ValueError(
                "Gmail credentials not configured. "
                "Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN"
            )
        
        response = requests.post(self.TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        })
        
        if response.status_code != 200:
            raise RuntimeError(f"Token refresh failed: {response.text}")
        
        self._access_token = response.json()["access_token"]
        return self._access_token
    
    @property
    def access_token(self) -> str:
        """Get or refresh access token."""
        if not self._access_token:
            self.get_access_token()
        return self._access_token
    
    def _create_mime_message(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
    ) -> str:
        """
        Create MIME message with optional attachments.
        
        Returns:
            Base64 URL-safe encoded message
        """
        if not attachments:
            # Simple plain text
            raw = f"To: {to}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
            return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
        
        # Multipart with attachments
        msg = MIMEMultipart()
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        for filepath in attachments:
            path = Path(filepath)
            if not path.exists():
                print(f"  ⚠️  Attachment not found: {filepath}")
                continue
            
            mime_type, _ = mimetypes.guess_type(str(path))
            if mime_type is None:
                mime_type = "application/octet-stream"
            
            main_type, sub_type = mime_type.split("/", 1)
            
            with open(path, "rb") as f:
                attachment = MIMEBase(main_type, sub_type)
                attachment.set_payload(f.read())
            
            encoders.encode_base64(attachment)
            attachment.add_header(
                "Content-Disposition", "attachment", filename=path.name
            )
            msg.attach(attachment)
            print(f"  📎 {path.name}")
        
        return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    
    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Create a Gmail draft.
        
        Args:
            to: Recipient email (can be empty for manual entry)
            subject: Email subject
            body: Email body text
            attachments: List of file paths to attach
            
        Returns:
            Draft ID if successful, None otherwise
        """
        raw_message = self._create_mime_message(to, subject, body, attachments)
        
        response = requests.post(
            f"{self.GMAIL_API}/drafts",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            },
            json={"message": {"raw": raw_message}}
        )
        
        if response.status_code in (200, 201):
            draft_id = response.json().get("id")
            return draft_id
        else:
            print(f"❌ Draft creation failed: {response.status_code} - {response.text}")
            return None
    
    def list_drafts(self, max_results: int = 10) -> list:
        """List existing drafts."""
        response = requests.get(
            f"{self.GMAIL_API}/drafts",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={"maxResults": max_results}
        )
        
        if response.status_code == 200:
            return response.json().get("drafts", [])
        return []
