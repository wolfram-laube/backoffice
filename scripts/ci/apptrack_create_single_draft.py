#!/usr/bin/env python3
"""Create a single Gmail draft from portal-triggered pipeline.

CI job: apptrack:create-draft
Triggered by portal with DRAFT_DATA_B64 variable.

Usage:
    DRAFT_DATA_B64=<base64> python scripts/ci/apptrack_create_single_draft.py
"""
import base64
import json
import logging
import os
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

CORP_PROJECT_ID = os.getenv("CORP_PROJECT_ID", "77075415")
GITLAB_TOKEN = os.getenv("GITLAB_API_TOKEN", "")
ATTACHMENT_PATHS = {
    "Profil_Laube_w_Summary_DE.pdf": "generated/typst-invoices",  # fallback paths
    "Profil_Laube_w_Summary_EN.pdf": "generated/typst-invoices",
    "Studienerfolg_08900915_1.pdf": "identity",
}


def get_gmail_token():
    """Get Gmail OAuth access token."""
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        logger.error("Gmail credentials not configured")
        return None

    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    if resp.status_code != 200:
        logger.error(f"Token error: {resp.text}")
        return None
    return resp.json()["access_token"]


def download_attachment(filename: str) -> bytes | None:
    """Download attachment from corporate repo or local project files."""
    # Try local /mnt/project first
    local = Path("/mnt/project") / filename
    if local.exists():
        return local.read_bytes()

    # Try corporate repo via GitLab API
    if not GITLAB_TOKEN:
        logger.warning(f"No GitLab token for attachment download: {filename}")
        return None

    # Search in known paths
    for path_prefix in ["identity", "generated", "sales", ""]:
        file_path = f"{path_prefix}/{filename}" if path_prefix else filename
        encoded = requests.utils.quote(file_path, safe="")
        resp = requests.get(
            f"https://gitlab.com/api/v4/projects/{CORP_PROJECT_ID}/repository/files/{encoded}/raw",
            headers={"PRIVATE-TOKEN": GITLAB_TOKEN},
            params={"ref": "main"},
        )
        if resp.status_code == 200:
            logger.info(f"Downloaded attachment: {file_path}")
            return resp.content

    logger.warning(f"Attachment not found: {filename}")
    return None


def create_gmail_draft(token: str, draft: dict) -> str | None:
    """Create Gmail draft with attachments."""
    to = draft.get("to", "")
    subject = draft.get("subject", "")
    body = draft.get("body", "")
    attachment_files = draft.get("attachments", [])

    if attachment_files:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain", "utf-8"))
        for filename in attachment_files:
            data = download_attachment(filename)
            if data:
                att = MIMEApplication(data, Name=filename)
                att["Content-Disposition"] = f'attachment; filename="{filename}"'
                msg.attach(att)
                logger.info(f"  Attached: {filename} ({len(data)} bytes)")
    else:
        msg = MIMEText(body, "plain", "utf-8")

    msg["to"] = to
    msg["subject"] = subject
    msg["from"] = "wolfram.laube@blauweiss-edv.at"

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    resp = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": {"raw": raw}},
    )

    if resp.status_code == 200:
        draft_id = resp.json()["id"]
        logger.info(f"✅ Gmail draft created: {draft_id}")
        return draft_id
    else:
        logger.error(f"Draft creation failed: {resp.status_code} {resp.text}")
        return None


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    draft_b64 = os.getenv("DRAFT_DATA_B64", "")
    if not draft_b64:
        logger.error("No DRAFT_DATA_B64 provided")
        return 1

    try:
        drafts = json.loads(base64.b64decode(draft_b64).decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to decode draft data: {e}")
        return 1

    if not drafts:
        logger.info("No drafts to create")
        return 0

    token = get_gmail_token()
    if not token:
        # Dry run — save draft data for debugging
        os.makedirs("output", exist_ok=True)
        with open("output/apptrack_draft_dryrun.json", "w") as f:
            json.dump(drafts, f, indent=2, ensure_ascii=False)
        logger.warning("No Gmail token — saved dry run to output/")
        return 0

    results = []
    for draft in drafts:
        logger.info(f"Creating draft: {draft.get('subject', '?')}")
        logger.info(f"  To: {draft.get('to', '(empty)')}")
        logger.info(f"  Attachments: {draft.get('attachments', [])}")
        draft_id = create_gmail_draft(token, draft)
        results.append({
            "subject": draft.get("subject"),
            "to": draft.get("to"),
            "draft_id": draft_id,
            "success": draft_id is not None,
        })

    os.makedirs("output", exist_ok=True)
    with open("output/apptrack_draft_results.json", "w") as f:
        json.dump(results, f, indent=2)

    success = sum(1 for r in results if r["success"])
    logger.info(f"Created {success}/{len(results)} drafts")
    return 0 if success == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
