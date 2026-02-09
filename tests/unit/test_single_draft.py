"""Tests for apptrack_create_single_draft.py — Sprint 5 Debt (#57).

Covers:
  - Gmail OAuth token retrieval
  - Draft data decoding (base64)
  - Email MIME construction (plain text + attachments)
  - Attachment download fallback logic
  - Error handling (missing credentials, bad data, API failure)
  - Dry-run mode (no Gmail token)
  - Main function end-to-end
"""
import base64
import json
import os
import sys
from email import message_from_bytes
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ci.apptrack_create_single_draft import (
    get_gmail_token,
    download_attachment,
    create_gmail_draft,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    """Clear Gmail env vars and set output dir."""
    for var in ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN",
                "DRAFT_DATA_B64", "GITLAB_API_TOKEN"]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)


def _draft_b64(drafts: list) -> str:
    """Encode draft list to base64."""
    return base64.b64encode(json.dumps(drafts).encode()).decode()


SAMPLE_DRAFT = {
    "to": "fynn.reuter@amoriabond.com",
    "subject": "Bewerbung: Cloud Architect",
    "body": "Sehr geehrte Damen und Herren...",
    "attachments": [],
    "profile": "wolfram",
    "project_id": "2965754",
}


# ---------------------------------------------------------------------------
# TestGetGmailToken
# ---------------------------------------------------------------------------

class TestGetGmailToken:
    """Test Gmail OAuth token retrieval."""

    def test_missing_credentials(self, monkeypatch):
        result = get_gmail_token()
        assert result is None

    def test_partial_credentials(self, monkeypatch):
        monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
        monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
        # Missing REFRESH_TOKEN
        result = get_gmail_token()
        assert result is None

    @patch("scripts.ci.apptrack_create_single_draft.requests.post")
    def test_successful_token(self, mock_post, monkeypatch):
        monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
        monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
        monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"access_token": "ya29.test_token"},
        )
        token = get_gmail_token()
        assert token == "ya29.test_token"
        mock_post.assert_called_once()
        call_data = mock_post.call_args[1]["data"]
        assert call_data["grant_type"] == "refresh_token"

    @patch("scripts.ci.apptrack_create_single_draft.requests.post")
    def test_token_api_error(self, mock_post, monkeypatch):
        monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
        monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
        monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
        mock_post.return_value = MagicMock(
            status_code=401, text="invalid_grant"
        )
        token = get_gmail_token()
        assert token is None


# ---------------------------------------------------------------------------
# TestDownloadAttachment
# ---------------------------------------------------------------------------

class TestDownloadAttachment:
    """Test attachment download with fallback logic."""

    def test_local_file_found(self, tmp_path, monkeypatch):
        """When /mnt/project/<file> exists, return its bytes."""
        fake_local = tmp_path / "Profil_Laube.pdf"
        fake_local.write_bytes(b"%PDF-1.4 fake")

        # Patch Path("/mnt/project") / filename to return our temp path
        original_path = Path

        def patched_path_new(*args):
            p = original_path(*args)
            return p

        with patch.object(Path, "__truediv__", wraps=Path.__truediv__):
            # Simpler: just make /mnt/project point to tmp_path
            with patch(
                "scripts.ci.apptrack_create_single_draft.Path.__truediv__",
            ) as mock_div:
                mock_div.return_value = fake_local
                result = download_attachment("Profil_Laube.pdf")
                assert result == b"%PDF-1.4 fake"

    @patch("scripts.ci.apptrack_create_single_draft.requests.get")
    def test_corporate_repo_download(self, mock_get, monkeypatch, tmp_path):
        """When local file missing, download from corporate GitLab repo."""
        monkeypatch.setenv("GITLAB_API_TOKEN", "glpat-test")
        # Reload module-level GITLAB_TOKEN
        import scripts.ci.apptrack_create_single_draft as mod
        monkeypatch.setattr(mod, "GITLAB_TOKEN", "glpat-test")

        mock_get.return_value = MagicMock(status_code=200, content=b"%PDF-data")

        fake_local = tmp_path / "nope.pdf"  # Does not exist
        with patch(
            "scripts.ci.apptrack_create_single_draft.Path.__truediv__",
            return_value=fake_local,
        ):
            result = download_attachment("Profil_Laube.pdf")
            assert result == b"%PDF-data"
            assert mock_get.called

    @patch("scripts.ci.apptrack_create_single_draft.requests.get")
    def test_attachment_not_found(self, mock_get, monkeypatch, tmp_path):
        """When neither local nor corporate has the file, return None."""
        import scripts.ci.apptrack_create_single_draft as mod
        monkeypatch.setattr(mod, "GITLAB_TOKEN", "glpat-test")

        mock_get.return_value = MagicMock(status_code=404)

        fake_local = tmp_path / "nope.pdf"
        with patch(
            "scripts.ci.apptrack_create_single_draft.Path.__truediv__",
            return_value=fake_local,
        ):
            result = download_attachment("nonexistent.pdf")
            assert result is None

    def test_no_gitlab_token(self, monkeypatch, tmp_path):
        """Without GitLab token and no local file, return None."""
        import scripts.ci.apptrack_create_single_draft as mod
        monkeypatch.setattr(mod, "GITLAB_TOKEN", "")

        fake_local = tmp_path / "nope.pdf"
        with patch(
            "scripts.ci.apptrack_create_single_draft.Path.__truediv__",
            return_value=fake_local,
        ):
            result = download_attachment("file.pdf")
            assert result is None


# ---------------------------------------------------------------------------
# TestCreateGmailDraft
# ---------------------------------------------------------------------------

class TestCreateGmailDraft:
    """Test Gmail draft creation with MIME construction."""

    @patch("scripts.ci.apptrack_create_single_draft.requests.post")
    def test_plain_text_draft(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "draft_abc123"},
        )
        draft = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "Hello World",
            "attachments": [],
        }
        result = create_gmail_draft("ya29.token", draft)
        assert result == "draft_abc123"

        # Verify MIME was correct
        call_json = mock_post.call_args[1]["json"]
        raw_bytes = base64.urlsafe_b64decode(call_json["message"]["raw"])
        msg = message_from_bytes(raw_bytes)
        assert msg["to"] == "test@example.com"
        assert msg["subject"] == "Test Subject"

    @patch("scripts.ci.apptrack_create_single_draft.download_attachment")
    @patch("scripts.ci.apptrack_create_single_draft.requests.post")
    def test_draft_with_attachments(self, mock_post, mock_download):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "draft_with_att"},
        )
        mock_download.return_value = b"%PDF-1.4 fake CV"

        draft = {
            "to": "recruiter@company.com",
            "subject": "Bewerbung",
            "body": "Anbei mein CV.",
            "attachments": ["Profil_Laube.pdf"],
        }
        result = create_gmail_draft("ya29.token", draft)
        assert result == "draft_with_att"
        mock_download.assert_called_once_with("Profil_Laube.pdf")

        # Verify multipart MIME
        call_json = mock_post.call_args[1]["json"]
        raw_bytes = base64.urlsafe_b64decode(call_json["message"]["raw"])
        msg = message_from_bytes(raw_bytes)
        assert msg.is_multipart()
        parts = list(msg.walk())
        filenames = [p.get_filename() for p in parts if p.get_filename()]
        assert "Profil_Laube.pdf" in filenames

    @patch("scripts.ci.apptrack_create_single_draft.requests.post")
    def test_draft_api_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=403, text="Insufficient permissions"
        )
        result = create_gmail_draft("ya29.token", SAMPLE_DRAFT)
        assert result is None

    @patch("scripts.ci.apptrack_create_single_draft.download_attachment")
    @patch("scripts.ci.apptrack_create_single_draft.requests.post")
    def test_attachment_not_found_still_sends(self, mock_post, mock_download):
        """Draft is created even if attachment download fails."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "draft_no_att"},
        )
        mock_download.return_value = None  # Download failed

        draft = {
            "to": "test@test.com",
            "subject": "Test",
            "body": "Body",
            "attachments": ["missing.pdf"],
        }
        result = create_gmail_draft("ya29.token", draft)
        # Still creates draft (multipart but no actual attachment data)
        assert result == "draft_no_att"

    @patch("scripts.ci.apptrack_create_single_draft.requests.post")
    def test_from_address_set(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": "draft_from"},
        )
        create_gmail_draft("ya29.token", SAMPLE_DRAFT)
        call_json = mock_post.call_args[1]["json"]
        raw_bytes = base64.urlsafe_b64decode(call_json["message"]["raw"])
        msg = message_from_bytes(raw_bytes)
        assert "blauweiss" in msg["from"]


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    """Test main() function end-to-end."""

    def test_no_draft_data(self, monkeypatch):
        result = main()
        assert result == 1

    def test_bad_base64(self, monkeypatch):
        monkeypatch.setenv("DRAFT_DATA_B64", "not-valid-base64!!!")
        result = main()
        assert result == 1

    def test_empty_drafts(self, monkeypatch):
        monkeypatch.setenv("DRAFT_DATA_B64", _draft_b64([]))
        result = main()
        assert result == 0

    def test_dry_run_no_gmail_token(self, monkeypatch, tmp_path):
        """Without Gmail creds, save dry run JSON."""
        monkeypatch.setenv("DRAFT_DATA_B64", _draft_b64([SAMPLE_DRAFT]))
        result = main()
        assert result == 0
        dryrun = tmp_path / "output" / "apptrack_draft_dryrun.json"
        assert dryrun.exists()
        data = json.loads(dryrun.read_text())
        assert len(data) == 1
        assert data[0]["subject"] == "Bewerbung: Cloud Architect"

    @patch("scripts.ci.apptrack_create_single_draft.create_gmail_draft")
    @patch("scripts.ci.apptrack_create_single_draft.get_gmail_token")
    def test_full_flow_success(self, mock_token, mock_create, monkeypatch, tmp_path):
        mock_token.return_value = "ya29.test"
        mock_create.return_value = "draft_123"
        monkeypatch.setenv("DRAFT_DATA_B64", _draft_b64([SAMPLE_DRAFT]))

        result = main()
        assert result == 0
        mock_create.assert_called_once()
        results_file = tmp_path / "output" / "apptrack_draft_results.json"
        assert results_file.exists()
        data = json.loads(results_file.read_text())
        assert data[0]["success"] is True
        assert data[0]["draft_id"] == "draft_123"

    @patch("scripts.ci.apptrack_create_single_draft.create_gmail_draft")
    @patch("scripts.ci.apptrack_create_single_draft.get_gmail_token")
    def test_full_flow_failure(self, mock_token, mock_create, monkeypatch, tmp_path):
        mock_token.return_value = "ya29.test"
        mock_create.return_value = None  # API failure
        monkeypatch.setenv("DRAFT_DATA_B64", _draft_b64([SAMPLE_DRAFT]))

        result = main()
        assert result == 1
        results_file = tmp_path / "output" / "apptrack_draft_results.json"
        data = json.loads(results_file.read_text())
        assert data[0]["success"] is False


# ---------------------------------------------------------------------------
# TestDraftDataEncoding
# ---------------------------------------------------------------------------

class TestDraftDataEncoding:
    """Test base64 encoding/decoding of draft data."""

    def test_roundtrip_ascii(self):
        original = [{"subject": "Hello", "body": "World"}]
        encoded = _draft_b64(original)
        decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
        assert decoded == original

    def test_roundtrip_unicode(self):
        original = [{"subject": "Bewerbung: Müller GmbH", "body": "Grüße, Ö"}]
        encoded = _draft_b64(original)
        decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
        assert decoded[0]["subject"] == "Bewerbung: Müller GmbH"

    def test_multiple_drafts(self):
        original = [SAMPLE_DRAFT, {**SAMPLE_DRAFT, "to": "other@test.com"}]
        encoded = _draft_b64(original)
        decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
        assert len(decoded) == 2
