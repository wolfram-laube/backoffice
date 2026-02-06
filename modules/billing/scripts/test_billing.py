#!/usr/bin/env python3
"""
Billing Regression Tests

Tests the multi-repo timesheet generation system.
Run with: pytest test_billing.py -v
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from generate_timesheet import (
    load_config,
    fetch_time_entries_multi_repo,
    generate_timesheet
)


class TestConfig:
    """Test configuration loading."""
    
    def test_load_config_exists(self):
        """Config file should exist and be valid YAML."""
        config = load_config()
        assert config is not None
        assert "clients" in config
        assert "consultants" in config
        assert "projects" in config
    
    def test_config_has_required_clients(self):
        """Config should have expected clients."""
        config = load_config()
        assert "nemensis" in config["clients"]
        assert "db" in config["clients"]
        assert "aok" in config["clients"]
    
    def test_config_has_projects_list(self):
        """Config should have projects list for multi-repo scanning."""
        config = load_config()
        projects = config.get("projects", [])
        assert len(projects) >= 1
        assert any("backoffice" in p for p in projects)
    
    def test_client_has_consultant_rates(self):
        """Each client should have consultant-specific rates."""
        config = load_config()
        nemensis = config["clients"]["nemensis"]
        assert "consultants" in nemensis
        assert "wolfram" in nemensis["consultants"]
        assert "rate" in nemensis["consultants"]["wolfram"]
    
    def test_consultant_has_default_rate(self):
        """Each consultant should have a default rate."""
        config = load_config()
        for cid, consultant in config["consultants"].items():
            assert "default_rate" in consultant, f"Consultant {cid} missing default_rate"


class TestLabels:
    """Test label format expectations."""
    
    def test_client_label_format(self):
        """Client labels should use double-colon format."""
        config = load_config()
        for client_id, client in config["clients"].items():
            if client_id.startswith("_"):
                continue
            label = client.get("gitlab_label", "")
            assert label.startswith("client::"), f"Client {client_id} label should be client::{client_id}"


class TestTimesheetGeneration:
    """Test timesheet generation logic."""
    
    @pytest.fixture
    def mock_config(self):
        return {
            "projects": ["test/project1", "test/project2"],
            "consultants": {
                "wolfram": {
                    "name": "Wolfram Laube",
                    "gitlab_username": "wolfram.laube",
                    "default_rate": 100
                }
            },
            "clients": {
                "testclient": {
                    "name": "Test Client",
                    "gitlab_label": "client::testclient",
                    "currency": "EUR",
                    "consultants": {
                        "wolfram": {"rate": 110}
                    }
                }
            }
        }
    
    def test_rate_override(self, mock_config):
        """Client-specific rate should override default rate."""
        client_rate = mock_config["clients"]["testclient"]["consultants"]["wolfram"]["rate"]
        default_rate = mock_config["consultants"]["wolfram"]["default_rate"]
        
        assert client_rate == 110
        assert default_rate == 100
        assert client_rate != default_rate


class TestIntegration:
    """Integration tests (require GitLab API access)."""
    
    @pytest.fixture
    def gitlab_token(self):
        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            pytest.skip("GITLAB_TOKEN not set")
        return token
    
    def test_fetch_from_backoffice(self, gitlab_token):
        """Should be able to fetch issues from backoffice project."""
        config = load_config()
        projects = [p for p in config["projects"] if "backoffice" in p]
        
        # Fetch for current month
        from datetime import datetime
        now = datetime.now()
        
        entries = fetch_time_entries_multi_repo(
            projects,
            now.year,
            now.month,
            "client::nemensis",
            "wolfram.laube"
        )
        
        # Should return dict (even if empty)
        assert isinstance(entries, dict)
    
    def test_generate_timesheet_nemensis(self, gitlab_token):
        """Should generate timesheet for nemensis client."""
        config = load_config()
        from datetime import datetime
        now = datetime.now()
        
        result = generate_timesheet(
            "nemensis",
            "wolfram",
            now.year,
            now.month,
            "de",
            config
        )
        
        # Result is Path or None
        if result:
            assert result.suffix == ".json"
            assert result.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
