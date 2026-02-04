"""
Backoffice Test Configuration

Shared fixtures for all tests.
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any


# =============================================================================
# FIXTURES: Sample Data
# =============================================================================

@pytest.fixture
def sample_issues() -> List[Dict]:
    """Sample CRM issues for testing."""
    return [
        {
            "iid": 1,
            "title": "[Etengo AG] Senior Python Developer",
            "state": "opened",
            "created_at": "2026-01-15T10:00:00Z",
            "updated_at": "2026-01-20T14:30:00Z",
            "labels": ["status::versendet", "rate::105+", "tech::python", "hot-lead"],
        },
        {
            "iid": 2,
            "title": "[Hays AG] DevOps Engineer",
            "state": "opened",
            "created_at": "2026-01-10T09:00:00Z",
            "updated_at": "2026-01-10T09:00:00Z",
            "labels": ["status::versendet", "rate::95-105", "tech::kubernetes"],
        },
        {
            "iid": 3,
            "title": "[Direct] Cloud Architect",
            "state": "closed",
            "created_at": "2026-01-05T08:00:00Z",
            "updated_at": "2026-01-18T16:00:00Z",
            "labels": ["status::absage", "rate::105+", "tech::aws"],
        },
        {
            "iid": 4,
            "title": "[Computer Futures] ML Engineer",
            "state": "opened",
            "created_at": "2026-01-20T11:00:00Z",
            "updated_at": "2026-01-25T10:00:00Z",
            "labels": ["status::interview", "rate::105+", "tech::python", "tech::ai", "hot-lead"],
        },
        {
            "iid": 5,
            "title": "[SOLCOM] Data Engineer",
            "state": "opened",
            "created_at": "2026-01-22T09:00:00Z",
            "updated_at": "2026-01-22T09:00:00Z",
            "labels": ["status::neu", "rate::95-105"],
        },
    ]


@pytest.fixture
def sample_applications() -> List[Dict]:
    """Sample job applications for testing."""
    return [
        {
            "date_recorded": "2026-01-15",
            "project_title": "Senior Python Developer - Energy Sector",
            "provider": "Etengo AG",
            "contact_name": "Max Mustermann",
            "contact_email": "max@etengo.de",
            "location": "Berlin",
            "rate_eur_h": "110",
            "status": "versendet",
            "notes": "Match: 95%",
        },
        {
            "date_recorded": "2026-01-16",
            "project_title": "DevOps Engineer - Kubernetes",
            "provider": "Hays AG",
            "contact_name": "Lisa Schmidt",
            "contact_email": "lisa@hays.de",
            "location": "München",
            "rate_eur_h": "100",
            "status": "versendet",
            "notes": "Match: 88%",
        },
    ]


# =============================================================================
# FIXTURES: GitLab API Mock
# =============================================================================

@pytest.fixture
def mock_gitlab_api(sample_issues):
    """Mock GitLab API responses."""
    
    def api_handler(endpoint: str, method: str = "GET", data: dict = None):
        # GET /projects/{id}/issues
        if "/issues" in endpoint and method == "GET":
            return sample_issues
        
        # GET /projects/{id}/issues/{iid}
        if "/issues/" in endpoint and method == "GET":
            iid = int(endpoint.split("/issues/")[1].split("/")[0])
            return next((i for i in sample_issues if i["iid"] == iid), None)
        
        # PUT /projects/{id}/issues/{iid}
        if "/issues/" in endpoint and method == "PUT":
            return {"iid": 1, "state": "opened", **data}
        
        # POST /projects/{id}/issues/{iid}/notes
        if "/notes" in endpoint and method == "POST":
            return {"id": 999, "body": data.get("body", "")}
        
        return None
    
    return api_handler


@pytest.fixture
def mock_env_gitlab():
    """Set up GitLab environment variables."""
    with patch.dict(os.environ, {
        "GITLAB_TOKEN": "test-token-12345",
        "CRM_PROJECT_ID": "78171527",
    }):
        yield


# =============================================================================
# FIXTURES: Date/Time
# =============================================================================

@pytest.fixture
def frozen_time():
    """Freeze time for consistent test results."""
    from datetime import datetime
    
    class FrozenDatetime:
        @staticmethod
        def now():
            return datetime(2026, 2, 1, 12, 0, 0)
    
    with patch('datetime.datetime', FrozenDatetime):
        yield FrozenDatetime


# =============================================================================
# HELPERS
# =============================================================================

def normalize_labels(issue: Dict) -> List[str]:
    """Normalize labels to list of strings."""
    labels = issue.get("labels", [])
    return [l["name"] if isinstance(l, dict) else l for l in labels]
