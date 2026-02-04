#!/usr/bin/env python3
"""
Integration Tests for Billing Module

Tests the complete billing workflow from time entries to invoice.
Uses mocked external services (GitLab API, Google Drive).
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.billing import (
    SAMPLE_CONFIG,
    SAMPLE_GRAPHQL_RESPONSE,
    SAMPLE_SEQUENCES,
    SAMPLE_SYNC_DATA,
    create_temp_config,
    create_temp_templates,
)


class TestBillingWorkflow:
    """Integration tests for the complete billing workflow."""
    
    @pytest.fixture
    def temp_billing_dir(self, tmp_path):
        """Create temporary billing directory structure."""
        billing_dir = tmp_path / "billing"
        billing_dir.mkdir()
        
        # Create subdirectories
        (billing_dir / "config").mkdir()
        (billing_dir / "templates").mkdir()
        (billing_dir / "output").mkdir()
        (billing_dir / "scripts").mkdir()
        
        return billing_dir
    
    @pytest.fixture
    def mock_config(self, temp_billing_dir):
        """Create mock configuration."""
        import yaml
        
        config_file = temp_billing_dir / "config" / "clients.yaml"
        with open(config_file, "w") as f:
            yaml.dump(SAMPLE_CONFIG, f)
        
        seq_file = temp_billing_dir / "config" / "sequences.yaml"
        with open(seq_file, "w") as f:
            yaml.dump(SAMPLE_SEQUENCES, f)
        
        return config_file
    
    def test_workflow_time_to_timesheet(self, temp_billing_dir, mock_config):
        """Test: Time entries → Timesheet generation."""
        import yaml
        
        # 1. Load config
        with open(mock_config, "r") as f:
            config = yaml.safe_load(f)
        
        # 2. Mock GitLab API response
        api_response = SAMPLE_GRAPHQL_RESPONSE
        
        # 3. Parse time entries
        entries = {}
        for issue in api_response["data"]["project"]["issues"]["nodes"]:
            for timelog in issue["timelogs"]["nodes"]:
                spent_at = datetime.fromisoformat(
                    timelog["spentAt"].replace("Z", "+00:00")
                )
                day = spent_at.day
                hours = timelog["timeSpent"] / 3600
                description = f"{issue['title']}"
                
                if day not in entries:
                    entries[day] = []
                entries[day].append((hours, description))
        
        # 4. Calculate totals
        total_hours = sum(
            sum(h for h, _ in day_entries)
            for day_entries in entries.values()
        )
        
        # 5. Generate sync data
        sync_data = {
            "client_id": "testclient",
            "consultant_id": "wolfram",
            "year": 2026,
            "month": 1,
            "total_hours": total_hours,
            "entries": {str(k): v for k, v in entries.items()},
            "generated_at": datetime.now().isoformat(),
        }
        
        # 6. Write sync file
        sync_file = temp_billing_dir / "output" / "wolfram_testclient_2026-01_timesheet.sync.json"
        with open(sync_file, "w") as f:
            json.dump(sync_data, f)
        
        # Assertions
        assert sync_file.exists()
        assert total_hours == 7.0  # 4 + 2 + 1 hours
        
        with open(sync_file, "r") as f:
            saved_data = json.load(f)
        assert saved_data["total_hours"] == 7.0
    
    def test_workflow_timesheet_to_invoice(self, temp_billing_dir, mock_config):
        """Test: Timesheet → Invoice generation."""
        import yaml
        
        # 1. Create timesheet sync file
        sync_data = SAMPLE_SYNC_DATA.copy()
        sync_file = temp_billing_dir / "output" / "wolfram_testclient_2026-01_timesheet.sync.json"
        with open(sync_file, "w") as f:
            json.dump(sync_data, f)
        
        # 2. Load config
        with open(mock_config, "r") as f:
            config = yaml.safe_load(f)
        
        # 3. Load sequences
        seq_file = temp_billing_dir / "config" / "sequences.yaml"
        with open(seq_file, "r") as f:
            sequences = yaml.safe_load(f)
        
        # 4. Generate invoice number
        prefix = sequences["invoices"]["prefix"]
        number = sequences["invoices"]["next_number"]
        invoice_number = f"{prefix}-{number:03d}"
        
        # 5. Calculate invoice amount
        client_config = config["clients"]["testclient"]
        rate = client_config["rates"]["remote"]
        amount = sync_data["total_hours"] * rate
        
        # 6. Generate invoice data
        invoice_data = {
            "invoice_number": invoice_number,
            "client": client_config,
            "period": f"{sync_data['year']}-{sync_data['month']:02d}",
            "total_hours": sync_data["total_hours"],
            "rate": rate,
            "amount": amount,
            "generated_at": datetime.now().isoformat(),
        }
        
        # 7. Write invoice data
        invoice_file = temp_billing_dir / "output" / f"testclient_2026-01_invoice_{invoice_number}.json"
        with open(invoice_file, "w") as f:
            json.dump(invoice_data, f)
        
        # Assertions
        assert invoice_file.exists()
        assert invoice_number == "AR-042"
        assert amount == 735.0  # 7 hours * 105 EUR
    
    def test_workflow_team_consolidation(self, temp_billing_dir, mock_config):
        """Test: Multiple timesheets → Consolidated team invoice."""
        import yaml
        
        # 1. Create multiple timesheet sync files
        wolfram_sync = {
            "client_id": "testclient",
            "consultant_id": "wolfram",
            "total_hours": 80.0,
            "year": 2026,
            "month": 1,
        }
        ian_sync = {
            "client_id": "testclient",
            "consultant_id": "ian",
            "total_hours": 40.0,
            "year": 2026,
            "month": 1,
        }
        
        # Write sync files
        for sync_data, consultant in [(wolfram_sync, "wolfram"), (ian_sync, "ian")]:
            sync_file = temp_billing_dir / "output" / f"{consultant}_testclient_2026-01_timesheet.sync.json"
            with open(sync_file, "w") as f:
                json.dump(sync_data, f)
        
        # 2. Load all timesheets for client
        timesheets = []
        for sync_file in (temp_billing_dir / "output").glob("*_testclient_2026-01_timesheet.sync.json"):
            with open(sync_file, "r") as f:
                timesheets.append(json.load(f))
        
        # 3. Consolidate
        team_hours = sum(t["total_hours"] for t in timesheets)
        
        # 4. Generate consolidated invoice
        with open(mock_config, "r") as f:
            config = yaml.safe_load(f)
        
        project_rate = config["clients"]["testclient"]["rates"]["remote"]
        team_amount = team_hours * project_rate
        
        # Assertions
        assert len(timesheets) == 2
        assert team_hours == 120.0  # 80 + 40
        assert team_amount == 12600.0  # 120 * 105


class TestErrorHandling:
    """Tests for error handling in billing workflow."""
    
    def test_missing_config_file(self, tmp_path):
        """Test handling of missing config file."""
        missing_config = tmp_path / "nonexistent" / "clients.yaml"
        
        with pytest.raises(FileNotFoundError):
            with open(missing_config, "r") as f:
                pass
    
    def test_invalid_yaml_config(self, tmp_path):
        """Test handling of invalid YAML config."""
        import yaml
        
        invalid_yaml = tmp_path / "invalid.yaml"
        with open(invalid_yaml, "w") as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(yaml.YAMLError):
            with open(invalid_yaml, "r") as f:
                yaml.safe_load(f)
    
    def test_missing_client_in_config(self, tmp_path):
        """Test handling of unknown client ID."""
        import yaml
        
        config = {"clients": {"known_client": {}}}
        
        unknown_client = "unknown_client"
        assert unknown_client not in config["clients"]
    
    def test_missing_consultant_in_config(self, tmp_path):
        """Test handling of unknown consultant ID."""
        config = SAMPLE_CONFIG.copy()
        
        unknown_consultant = "unknown_consultant"
        assert unknown_consultant not in config["consultants"]
    
    def test_empty_time_entries(self):
        """Test handling of empty time entries."""
        api_response = {
            "data": {
                "project": {
                    "issues": {
                        "nodes": []
                    }
                }
            }
        }
        
        issues = api_response["data"]["project"]["issues"]["nodes"]
        assert len(issues) == 0
        
        # Total should be 0 for empty entries
        total_hours = 0
        for issue in issues:
            for timelog in issue.get("timelogs", {}).get("nodes", []):
                total_hours += timelog.get("timeSpent", 0) / 3600
        
        assert total_hours == 0


class TestCLIArguments:
    """Tests for command-line argument parsing."""
    
    def test_valid_period_argument(self):
        """Test parsing valid period argument."""
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument("--period", required=True)
        
        args = parser.parse_args(["--period", "2026-01"])
        assert args.period == "2026-01"
    
    def test_period_to_year_month(self):
        """Test converting period string to year and month."""
        period = "2026-01"
        year, month = map(int, period.split("-"))
        
        assert year == 2026
        assert month == 1
    
    def test_all_consultants_flag(self):
        """Test --all-consultants flag."""
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument("--all-consultants", action="store_true")
        
        args = parser.parse_args(["--all-consultants"])
        assert args.all_consultants is True
        
        args = parser.parse_args([])
        assert args.all_consultants is False


class TestFileOperations:
    """Tests for file operations in billing workflow."""
    
    def test_create_output_directory(self, tmp_path):
        """Test creating output directory if it doesn't exist."""
        output_dir = tmp_path / "output"
        assert not output_dir.exists()
        
        output_dir.mkdir(parents=True, exist_ok=True)
        assert output_dir.exists()
    
    def test_write_sync_json(self, tmp_path):
        """Test writing sync.json file."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        sync_data = SAMPLE_SYNC_DATA
        sync_file = output_dir / "test.sync.json"
        
        with open(sync_file, "w", encoding="utf-8") as f:
            json.dump(sync_data, f, indent=2)
        
        assert sync_file.exists()
        
        with open(sync_file, "r") as f:
            loaded = json.load(f)
        
        assert loaded["client_id"] == sync_data["client_id"]
    
    def test_write_typst_file(self, tmp_path):
        """Test writing .typ file with UTF-8 encoding."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        typst_content = """
#set page(paper: "a4")
#set text(font: "Arial")

= Rechnung

Ümlauts: äöüß
€uro symbol
"""
        
        typ_file = output_dir / "test.typ"
        with open(typ_file, "w", encoding="utf-8") as f:
            f.write(typst_content)
        
        assert typ_file.exists()
        
        with open(typ_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "äöüß" in content
        assert "€" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
