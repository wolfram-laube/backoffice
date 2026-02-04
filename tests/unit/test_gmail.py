"""
Unit Tests for Gmail Module
===========================
"""

import base64
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ============================================================================
# Profile Tests
# ============================================================================

class TestProfiles:
    """Tests for profile loading."""
    
    def test_load_profiles_returns_dict(self, tmp_path):
        """Load profiles should return dict with profiles and teams."""
        config = tmp_path / "profiles.yaml"
        config.write_text("""
profiles:
  test_user:
    name: "Test User"
    email: "test@example.com"
teams:
  test_team:
    members: ["test_user"]
""")
        from modules.gmail.profiles import load_profiles
        result = load_profiles(config)
        
        assert "profiles" in result
        assert "teams" in result
        assert "test_user" in result["profiles"]
    
    def test_load_profile_single(self, tmp_path):
        """Load single profile by key."""
        config = tmp_path / "profiles.yaml"
        config.write_text("""
profiles:
  wolfram:
    name: "Wolfram Laube"
    email: "wolfram@test.com"
    rate: "105"
defaults:
  attachments_dir: "attachments"
""")
        from modules.gmail.profiles import load_profile
        profile = load_profile("wolfram", config)
        
        assert profile["name"] == "Wolfram Laube"
        assert profile["email"] == "wolfram@test.com"
        assert profile["key"] == "wolfram"
        assert profile["attachments_dir"] == "attachments"  # from defaults
    
    def test_load_profile_not_found(self, tmp_path):
        """Unknown profile should raise KeyError."""
        config = tmp_path / "profiles.yaml"
        config.write_text("profiles: {}")
        
        from modules.gmail.profiles import load_profile
        with pytest.raises(KeyError, match="not found"):
            load_profile("nonexistent", config)
    
    def test_get_team_config(self, tmp_path):
        """Load team configuration with member details."""
        config = tmp_path / "profiles.yaml"
        config.write_text("""
profiles:
  user1:
    name: "User One"
    email: "user1@test.com"
    attachments: ["cv1.pdf"]
  user2:
    name: "User Two"
    attachments: ["cv2.pdf"]
teams:
  duo:
    members: ["user1", "user2"]
    primary_contact: "user1"
    pitch: "Dynamic duo"
""")
        from modules.gmail.profiles import get_team_config
        team = get_team_config("duo", config)
        
        assert "members" in team
        assert len(team["members"]) == 2
        assert team["email"] == "user1@test.com"
        assert len(team["attachments"]) == 2
    
    def test_list_available_profiles(self, tmp_path):
        """List all profiles and teams."""
        config = tmp_path / "profiles.yaml"
        config.write_text("""
profiles:
  a: {}
  b: {}
teams:
  team1: {}
""")
        from modules.gmail.profiles import list_available_profiles
        result = list_available_profiles(config)
        
        assert set(result["profiles"]) == {"a", "b"}
        assert result["teams"] == ["team1"]


# ============================================================================
# Drafter Tests
# ============================================================================

class TestDrafter:
    """Tests for email generation."""
    
    @pytest.fixture
    def config_file(self, tmp_path):
        """Create test config file."""
        config = tmp_path / "profiles.yaml"
        config.write_text("""
profiles:
  wolfram:
    name: "Wolfram Laube"
    email: "wolfram@test.com"
    rate: "105"
    signature: "Best, Wolfram"
    attachments: []
    skills:
      primary: ["kubernetes", "python", "ai"]
teams:
  test_team:
    members: ["wolfram"]
    primary_contact: "wolfram"
    pitch: "Test Team"
defaults:
  attachments_dir: "attachments"
""")
        return config
    
    def test_generate_basic_email(self, config_file):
        """Generate basic email with subject and body."""
        from modules.gmail.drafter import Drafter
        drafter = Drafter(profile_key="wolfram", config_path=config_file)
        
        email = drafter.generate(
            project_title="DevOps Engineer",
            contact_email="hr@example.com"
        )
        
        assert email["to"] == "hr@example.com"
        assert "Bewerbung:" in email["subject"]
        assert "DevOps" in email["subject"]
        assert "Wolfram Laube" in email["body"] or "105" in email["body"]
    
    def test_generate_ai_project_body(self, config_file):
        """AI project should include AI-specific content."""
        from modules.gmail.drafter import Drafter
        drafter = Drafter(profile_key="wolfram", config_path=config_file)
        
        email = drafter.generate(
            project_title="Senior AI/ML Engineer - LLM Development",
            contact_email="ai@example.com"
        )
        
        assert any(kw in email["body"].lower() for kw in ["ai", "ml", "jku", "bachelor"])
    
    def test_generate_kubernetes_project_body(self, config_file):
        """Kubernetes project should include K8s content."""
        from modules.gmail.drafter import Drafter
        drafter = Drafter(profile_key="wolfram", config_path=config_file)
        
        email = drafter.generate(project_title="Kubernetes Platform Engineer")
        
        assert any(kw in email["body"].lower() for kw in ["cka", "ckad", "kubernetes"])
    
    def test_generate_includes_signature(self, config_file):
        """Email should include profile signature."""
        from modules.gmail.drafter import Drafter
        drafter = Drafter(profile_key="wolfram", config_path=config_file)
        
        email = drafter.generate(project_title="Test Position")
        
        assert "Best, Wolfram" in email["body"]
    
    def test_generate_includes_project_url(self, config_file):
        """Email should include project URL if provided."""
        from modules.gmail.drafter import Drafter
        drafter = Drafter(profile_key="wolfram", config_path=config_file)
        
        email = drafter.generate(
            project_title="Test",
            project_url="https://example.com/job/123"
        )
        
        assert "https://example.com/job/123" in email["body"]
    
    def test_generate_subject_truncation(self, config_file):
        """Long titles should be truncated in subject."""
        from modules.gmail.drafter import Drafter
        drafter = Drafter(profile_key="wolfram", config_path=config_file)
        
        long_title = "A" * 100
        email = drafter.generate(project_title=long_title)
        
        assert len(email["subject"]) < 70
        assert "..." in email["subject"]
    
    def test_convenience_function(self, config_file):
        """Test generate_email convenience function."""
        from modules.gmail.drafter import generate_email
        
        # Patch to use our config
        with patch("modules.gmail.drafter.get_profile_or_team") as mock:
            mock.return_value = {
                "name": "Test",
                "rate": "100",
                "signature": "Sig",
                "attachments": [],
            }
            email = generate_email(
                project_title="Test",
                profile_key="wolfram",
                contact_email="test@test.com"
            )
        
        assert email["to"] == "test@test.com"


# ============================================================================
# Client Tests
# ============================================================================

class TestGmailClient:
    """Tests for Gmail API client."""
    
    def test_is_configured_false_without_env(self):
        """Client should report unconfigured without credentials."""
        from modules.gmail.client import GmailClient
        
        with patch.dict("os.environ", {}, clear=True):
            client = GmailClient()
            assert not client.is_configured
    
    def test_is_configured_true_with_all_creds(self):
        """Client should report configured with all credentials."""
        from modules.gmail.client import GmailClient
        
        client = GmailClient(
            client_id="id",
            client_secret="secret",
            refresh_token="token"
        )
        assert client.is_configured
    
    @patch("modules.gmail.client.requests.post")
    def test_get_access_token_success(self, mock_post):
        """Should get access token from refresh token."""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"access_token": "new_token"}
        )
        
        from modules.gmail.client import GmailClient
        client = GmailClient(
            client_id="id",
            client_secret="secret",
            refresh_token="refresh"
        )
        
        token = client.get_access_token()
        assert token == "new_token"
    
    @patch("modules.gmail.client.requests.post")
    def test_get_access_token_failure(self, mock_post):
        """Should raise on token refresh failure."""
        mock_post.return_value = Mock(
            status_code=400,
            text="Invalid grant"
        )
        
        from modules.gmail.client import GmailClient
        client = GmailClient(
            client_id="id",
            client_secret="secret",
            refresh_token="bad_refresh"
        )
        
        with pytest.raises(RuntimeError, match="Token refresh failed"):
            client.get_access_token()
    
    @patch("modules.gmail.client.requests.post")
    def test_create_draft_success(self, mock_post):
        """Should create draft and return ID."""
        # First call for token, second for draft
        mock_post.side_effect = [
            Mock(status_code=200, json=lambda: {"access_token": "token"}),
            Mock(status_code=200, json=lambda: {"id": "draft_123"}),
        ]
        
        from modules.gmail.client import GmailClient
        client = GmailClient(
            client_id="id",
            client_secret="secret",
            refresh_token="refresh"
        )
        
        draft_id = client.create_draft(
            to="test@example.com",
            subject="Test Subject",
            body="Test body"
        )
        
        assert draft_id == "draft_123"
    
    def test_create_mime_simple(self):
        """Should create simple MIME message without attachments."""
        from modules.gmail.client import GmailClient
        client = GmailClient()
        
        raw = client._create_mime_message(
            to="test@example.com",
            subject="Test",
            body="Body text"
        )
        
        decoded = base64.urlsafe_b64decode(raw).decode()
        assert "To: test@example.com" in decoded
        assert "Subject: Test" in decoded
        assert "Body text" in decoded


# ============================================================================
# Integration Tests
# ============================================================================

class TestCreateDraftsFromB64:
    """Tests for CI integration function."""
    
    def test_dry_run_prints_only(self, capsys):
        """Dry run should only print, not create."""
        from modules.gmail import create_drafts_from_b64
        
        drafts = [
            {"subject": "Test 1", "to": "a@b.com", "body": "Body 1"},
            {"subject": "Test 2", "to": "c@d.com", "body": "Body 2"},
        ]
        drafts_b64 = base64.b64encode(json.dumps(drafts).encode()).decode()
        
        count = create_drafts_from_b64(drafts_b64, dry_run=True)
        
        assert count == 2
        captured = capsys.readouterr()
        assert "Test 1" in captured.out
        assert "Test 2" in captured.out
    
    @patch("modules.gmail.GmailClient")
    def test_creates_drafts(self, mock_client_class):
        """Should create drafts via client."""
        mock_client = Mock()
        mock_client.create_draft.return_value = "draft_id"
        mock_client_class.return_value = mock_client
        
        from modules.gmail import create_drafts_from_b64
        
        drafts = [{"subject": "Test", "to": "a@b.com", "body": "Body"}]
        drafts_b64 = base64.b64encode(json.dumps(drafts).encode()).decode()
        
        count = create_drafts_from_b64(drafts_b64, dry_run=False)
        
        assert count == 1
        mock_client.create_draft.assert_called_once()
