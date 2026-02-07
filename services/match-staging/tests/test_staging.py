"""Tests for Match Staging & Notification Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models import (
    JobMatch,
    MatchScore,
    MatchState,
    NotificationPayload,
    RequirementMatch,
    StagedMatch,
    StagingRequest,
)
from src.config import ServiceConfig, load_config


# --- Model Tests ---


class TestJobMatch:
    def test_score_tier_high(self):
        match = JobMatch(
            title="Test", provider="P", location="Wien",
            start_date="ASAP", duration="6Mo", overall_score=95,
        )
        assert match.score_tier == MatchScore.HIGH
        assert match.score_emoji == "🔥"

    def test_score_tier_medium(self):
        match = JobMatch(
            title="Test", provider="P", location="Wien",
            start_date="ASAP", duration="6Mo", overall_score=75,
        )
        assert match.score_tier == MatchScore.MEDIUM
        assert match.score_emoji == "✅"

    def test_default_rate(self):
        match = JobMatch(
            title="Test", provider="P", location="Wien",
            start_date="ASAP", duration="6Mo", overall_score=80,
        )
        assert match.rate_eur == 105


class TestNotificationPayload:
    def test_from_staged(self):
        match = JobMatch(
            title="Cloud Architect", provider="Amoria Bond",
            location="Heilbronn", start_date="ASAP", duration="3Mo+",
            overall_score=97,
        )
        staged = StagedMatch(
            match=match, gitlab_issue_id=1, gitlab_issue_iid=42,
            gitlab_issue_url="https://gitlab.com/test/42",
        )
        payload = NotificationPayload.from_staged(
            cycle_id="test-cycle",
            staged=[staged],
            review_url="https://gitlab.com/test",
        )
        assert payload.matches_count == 1
        assert "97%" in payload.summary
        assert "Cloud Architect" in payload.summary

    def test_summary_sorted_descending(self):
        matches = [
            JobMatch(
                title="Low", provider="P", location="W",
                start_date="X", duration="X", overall_score=70,
            ),
            JobMatch(
                title="High", provider="P", location="W",
                start_date="X", duration="X", overall_score=97,
            ),
        ]
        staged = [
            StagedMatch(
                match=m, gitlab_issue_id=i, gitlab_issue_iid=i,
                gitlab_issue_url=f"https://test/{i}",
            )
            for i, m in enumerate(matches)
        ]
        payload = NotificationPayload.from_staged("c", staged, "url")
        # High score should appear first in summary
        assert payload.summary.index("97%") < payload.summary.index("70%")


class TestStagingRequest:
    def test_defaults(self):
        req = StagingRequest(matches=[])
        assert req.attach_profile is True
        assert req.auto_notify is True
        assert req.cycle_id  # auto-generated


# --- Config Tests ---


class TestConfig:
    def test_defaults(self):
        config = ServiceConfig()
        assert config.notification.preferences.threshold == 70
        assert config.notification.channels.email.enabled is True
        assert config.notification.channels.slack.enabled is False
        assert config.notification.channels.gitlab_todo.assignee_id == 1349601

    @patch.dict("os.environ", {"CONFIG__NOTIFICATION__PREFERENCES__THRESHOLD": "85"})
    def test_env_override(self):
        config = load_config("/nonexistent.yml")
        assert config.notification.preferences.threshold == 85


# --- Adapter Tests (mocked) ---


class TestSlackAdapter:
    @pytest.mark.asyncio
    async def test_send_success(self):
        from src.adapters.slack_adapter import SlackAdapter
        from src.config import SlackConfig

        config = SlackConfig(enabled=True, webhook_url="https://hooks.slack.com/test")
        adapter = SlackAdapter(config)

        payload = NotificationPayload(
            cycle_id="test", matches_count=1,
            matches=[
                JobMatch(
                    title="Test", provider="P", location="W",
                    start_date="X", duration="X", overall_score=90,
                )
            ],
            summary="test", review_url="https://test",
        )

        with patch("src.adapters.slack_adapter.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "ok"
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                post=AsyncMock(return_value=mock_resp)
            ))
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await adapter.send(payload)
            assert result is True

    def test_disabled_when_no_url(self):
        from src.adapters.slack_adapter import SlackAdapter
        from src.config import SlackConfig

        adapter = SlackAdapter(SlackConfig(enabled=True, webhook_url=""))
        assert adapter.is_enabled is False


class TestWhatsAppAdapter:
    def test_disabled_without_credentials(self):
        from src.adapters.whatsapp_adapter import WhatsAppAdapter
        from src.config import WhatsAppConfig

        adapter = WhatsAppAdapter(WhatsAppConfig(enabled=True))
        assert adapter.is_enabled is False

    def test_message_truncation(self):
        from src.adapters.whatsapp_adapter import WhatsAppAdapter
        from src.config import WhatsAppConfig

        adapter = WhatsAppAdapter(WhatsAppConfig())
        payload = NotificationPayload(
            cycle_id="test", matches_count=8,
            matches=[
                JobMatch(
                    title=f"Job {i}", provider="P", location="W",
                    start_date="X", duration="X", overall_score=90 - i * 3,
                )
                for i in range(8)
            ],
            summary="test", review_url="https://test",
        )
        msg = adapter._build_message(payload)
        assert "+3 weitere" in msg  # 8 - 5 = 3 overflow


# --- Dispatcher Tests ---


class TestDispatcher:
    @patch("src.dispatcher.NotificationDispatcher._is_quiet_hours", return_value=True)
    @pytest.mark.asyncio
    async def test_quiet_hours_blocks(self, mock_qh):
        from src.dispatcher import NotificationDispatcher

        config = ServiceConfig()
        d = NotificationDispatcher(config)
        d.adapters = [MagicMock(channel_name="test")]

        payload = MagicMock()
        results = await d.dispatch(payload)
        assert results == {"test": False}

    @patch("src.dispatcher.NotificationDispatcher._is_quiet_hours", return_value=True)
    @pytest.mark.asyncio
    async def test_force_overrides_quiet_hours(self, mock_qh):
        from src.dispatcher import NotificationDispatcher

        config = ServiceConfig()
        d = NotificationDispatcher(config)

        mock_adapter = AsyncMock()
        mock_adapter.channel_name = "test"
        mock_adapter.send = AsyncMock(return_value=True)
        d.adapters = [mock_adapter]

        payload = MagicMock()
        results = await d.dispatch(payload, force=True)
        assert results == {"test": True}
