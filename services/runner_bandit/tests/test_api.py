"""Integration tests for the MAB service API."""
import pytest
from fastapi.testclient import TestClient
from src.webhook_handler import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    def test_root_returns_service_info(self, client):
        """GET / should return service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "algorithm" in data
        assert "runners" in data

    def test_stats_returns_runner_statistics(self, client):
        """GET /stats should return detailed statistics."""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_observations" in data
        assert "runners" in data


class TestRecommendEndpoint:
    def test_recommend_returns_runner(self, client):
        """GET /recommend should return a runner name."""
        response = client.get("/recommend")
        assert response.status_code == 200
        data = response.json()
        assert "recommended_runner" in data
        assert isinstance(data["recommended_runner"], str)

    def test_recommend_includes_exploration_info(self, client):
        """GET /recommend should include exploration details."""
        response = client.get("/recommend")
        data = response.json()
        assert "exploration_info" in data


class TestUpdateEndpoint:
    def test_update_with_valid_data(self, client):
        """POST /update should accept valid observation."""
        response = client.post("/update", json={
            "runner": "gitlab-runner-nordic",
            "success": True,
            "duration_seconds": 45.5,
            "cost": 0.0
        })
        assert response.status_code == 200
        data = response.json()
        assert "reward" in data
        assert data["reward"] > 0

    def test_update_with_failure(self, client):
        """POST /update with failure should return zero reward."""
        response = client.post("/update", json={
            "runner": "gitlab-runner-nordic",
            "success": False,
            "duration_seconds": 120.0,
            "cost": 0.0
        })
        assert response.status_code == 200
        data = response.json()
        assert data["reward"] == 0.0

    def test_update_with_unknown_runner(self, client):
        """POST /update with unknown runner should add it."""
        response = client.post("/update", json={
            "runner": "new-test-runner",
            "success": True,
            "duration_seconds": 30.0,
            "cost": 0.0
        })
        assert response.status_code == 200


class TestWebhookEndpoint:
    def test_webhook_ignores_non_job_events(self, client):
        """POST /webhooks/gitlab should ignore non-job events."""
        response = client.post("/webhooks/gitlab", json={
            "object_kind": "push",
            "event_name": "push"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_webhook_processes_completed_job(self, client):
        """POST /webhooks/gitlab should process completed jobs."""
        response = client.post("/webhooks/gitlab", json={
            "object_kind": "build",
            "build_status": "success",
            "build_duration": 45.5,
            "runner": {
                "description": "gitlab-runner-nordic"
            }
        })
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "recorded"
        assert "reward" in data

    def test_webhook_ignores_running_job(self, client):
        """POST /webhooks/gitlab should ignore running jobs."""
        response = client.post("/webhooks/gitlab", json={
            "object_kind": "build",
            "build_status": "running",
            "runner": {
                "description": "gitlab-runner-nordic"
            }
        })
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"


class TestResetEndpoint:
    def test_reset_clears_statistics(self, client):
        """POST /reset should clear all statistics."""
        # First add some data
        client.post("/update", json={
            "runner": "gitlab-runner-nordic",
            "success": True,
            "duration_seconds": 30.0,
            "cost": 0.0
        })
        
        # Reset
        response = client.post("/reset")
        assert response.status_code == 200
        
        # Verify reset
        stats = client.get("/stats").json()
        assert stats["total_observations"] == 0
