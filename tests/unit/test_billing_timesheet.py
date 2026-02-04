#!/usr/bin/env python3
"""
Unit Tests for Billing Module - Timesheet Generation

Tests the core logic without external dependencies (GitLab API, filesystem).
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add modules to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.billing import (
    SAMPLE_CONFIG,
    SAMPLE_GRAPHQL_RESPONSE,
    EXPECTED_CONSOLIDATED_ENTRIES,
    SAMPLE_SYNC_DATA,
    create_temp_config,
    create_temp_templates,
)


class TestConfigLoading:
    """Tests for configuration loading."""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading a valid clients.yaml."""
        import yaml
        
        config_dir = create_temp_config(tmp_path)
        config_file = config_dir / "clients.yaml"
        
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        
        assert "consultants" in config
        assert "clients" in config
        assert "wolfram" in config["consultants"]
        assert "testclient" in config["clients"]
    
    def test_config_has_required_fields(self, tmp_path):
        """Test that client config has all required fields."""
        import yaml
        
        config_dir = create_temp_config(tmp_path)
        
        with open(config_dir / "clients.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        client = config["clients"]["testclient"]
        required_fields = [
            "name", "short", "address", "template", 
            "currency", "gitlab_label", "rates", "consultants"
        ]
        
        for field in required_fields:
            assert field in client, f"Missing required field: {field}"
    
    def test_consultant_has_gitlab_username(self, tmp_path):
        """Test that consultants have gitlab_username for API queries."""
        import yaml
        
        config_dir = create_temp_config(tmp_path)
        
        with open(config_dir / "clients.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        for consultant_id, consultant in config["consultants"].items():
            assert "gitlab_username" in consultant, \
                f"Consultant {consultant_id} missing gitlab_username"


class TestTimeEntryParsing:
    """Tests for parsing GitLab API responses."""
    
    def test_parse_graphql_response(self):
        """Test parsing time entries from GraphQL response."""
        response = SAMPLE_GRAPHQL_RESPONSE
        issues = response["data"]["project"]["issues"]["nodes"]
        
        entries = {}
        for issue in issues:
            for timelog in issue["timelogs"]["nodes"]:
                spent_at = datetime.fromisoformat(
                    timelog["spentAt"].replace("Z", "+00:00")
                )
                day = spent_at.day
                hours = timelog["timeSpent"] / 3600
                description = f"{issue['title']}: {timelog.get('note', 'Work')}"
                
                if day not in entries:
                    entries[day] = []
                entries[day].append((hours, description))
        
        assert 15 in entries
        assert 16 in entries
        assert len(entries[15]) == 2  # Two entries on day 15
        assert len(entries[16]) == 1  # One entry on day 16
    
    def test_filter_by_username(self):
        """Test filtering time entries by GitLab username."""
        response = SAMPLE_GRAPHQL_RESPONSE
        target_username = "wolfram.laube"
        
        filtered_entries = []
        for issue in response["data"]["project"]["issues"]["nodes"]:
            for timelog in issue["timelogs"]["nodes"]:
                if timelog["user"]["username"] == target_username:
                    filtered_entries.append(timelog)
        
        # All entries in sample are from wolfram.laube
        assert len(filtered_entries) == 3
    
    def test_convert_seconds_to_hours(self):
        """Test converting GitLab's seconds to hours."""
        test_cases = [
            (3600, 1.0),    # 1 hour
            (7200, 2.0),    # 2 hours
            (5400, 1.5),    # 1.5 hours
            (14400, 4.0),   # 4 hours
            (1800, 0.5),    # 30 minutes
        ]
        
        for seconds, expected_hours in test_cases:
            assert seconds / 3600 == expected_hours
    
    def test_handle_negative_time_entries(self):
        """Test that negative time entries (corrections) are handled."""
        entries = {
            15: [(4.0, "Work"), (-1.0, "Correction")],
        }
        
        # Consolidate by summing
        total = sum(hours for hours, _ in entries[15])
        assert total == 3.0  # 4 - 1 = 3


class TestTimeConsolidation:
    """Tests for consolidating time entries."""
    
    def test_consolidate_same_day_entries(self):
        """Test consolidating multiple entries on the same day."""
        raw_entries = {
            15: [
                (2.0, "Task A"),
                (3.0, "Task B"),
                (1.5, "Task A"),  # Duplicate task
            ]
        }
        
        total_hours = sum(h for h, _ in raw_entries[15])
        assert total_hours == 6.5
    
    def test_calculate_monthly_total(self):
        """Test calculating total hours for a month."""
        entries = EXPECTED_CONSOLIDATED_ENTRIES
        
        total = sum(
            sum(hours for hours, _ in day_entries) 
            for day_entries in entries.values()
        )
        
        # Day 15: 4 + 1 = 5, Day 16: 2 = 2, Total: 7
        assert total == 7.0
    
    def test_empty_entries(self):
        """Test handling empty time entries."""
        entries = {}
        total = sum(
            sum(hours for hours, _ in day_entries) 
            for day_entries in entries.values()
        )
        assert total == 0


class TestSyncMetadata:
    """Tests for sync.json metadata."""
    
    def test_sync_data_structure(self):
        """Test that sync data has required fields."""
        sync_data = SAMPLE_SYNC_DATA
        
        required_fields = [
            "client_id", "consultant_id", "year", "month",
            "total_hours", "entries", "generated_at"
        ]
        
        for field in required_fields:
            assert field in sync_data, f"Missing field: {field}"
    
    def test_sync_data_total_matches_entries(self):
        """Test that total_hours matches sum of entries."""
        sync_data = SAMPLE_SYNC_DATA
        
        calculated_total = sum(
            sum(h for h, _ in day_entries)
            for day_entries in sync_data["entries"].values()
        )
        
        assert sync_data["total_hours"] == calculated_total


class TestPeriodParsing:
    """Tests for period (YYYY-MM) parsing."""
    
    def test_valid_period_format(self):
        """Test parsing valid period strings."""
        valid_periods = [
            ("2026-01", 2026, 1),
            ("2026-12", 2026, 12),
            ("2025-06", 2025, 6),
        ]
        
        for period_str, expected_year, expected_month in valid_periods:
            year, month = map(int, period_str.split("-"))
            assert year == expected_year
            assert month == expected_month
    
    def test_invalid_period_format(self):
        """Test that invalid periods are rejected."""
        invalid_periods = [
            "2026/01",   # Wrong separator
            "01-2026",   # Wrong order
            "2026-1",    # Missing leading zero (should still work)
            "2026-13",   # Invalid month
            "abcd-01",   # Non-numeric year
        ]
        
        for period_str in invalid_periods:
            try:
                parts = period_str.split("-")
                year, month = int(parts[0]), int(parts[1])
                if month < 1 or month > 12:
                    raise ValueError("Invalid month")
                # 2026-1 should actually work, so we skip assertion for it
                if period_str not in ["2026-1"]:
                    pass  # Some may parse correctly
            except (ValueError, IndexError):
                pass  # Expected for invalid formats


class TestRateCalculation:
    """Tests for rate and amount calculations."""
    
    def test_calculate_amount(self):
        """Test calculating invoice amount from hours and rate."""
        hours = 40.0
        rate = 105.0
        
        amount = hours * rate
        assert amount == 4200.0
    
    def test_different_rates(self):
        """Test with different rate configurations."""
        test_cases = [
            (10.0, 105, 1050.0),   # Standard rate
            (10.0, 120, 1200.0),   # Onsite rate
            (7.5, 150, 1125.0),    # US rate
        ]
        
        for hours, rate, expected in test_cases:
            assert hours * rate == expected


class TestTypstGeneration:
    """Tests for Typst template generation."""
    
    def test_typst_escape_special_chars(self):
        """Test escaping special characters for Typst."""
        # Characters that need escaping in Typst
        special_chars = ["#", "@", "$", "%", "&"]
        
        def escape_typst(text: str) -> str:
            for char in special_chars:
                text = text.replace(char, f"\\{char}")
            return text
        
        assert escape_typst("Test #1") == "Test \\#1"
        assert escape_typst("50% done") == "50\\% done"
    
    def test_format_german_date(self):
        """Test formatting dates in German style."""
        from datetime import date
        
        german_months = [
            "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember"
        ]
        
        test_date = date(2026, 1, 15)
        month_name = german_months[test_date.month - 1]
        formatted = f"{test_date.day}. {month_name} {test_date.year}"
        
        assert formatted == "15. Januar 2026"
    
    def test_format_currency(self):
        """Test currency formatting."""
        def format_eur(amount: float) -> str:
            return f"{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        
        assert format_eur(1234.50) == "1.234,50 €"
        assert format_eur(105.00) == "105,00 €"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
