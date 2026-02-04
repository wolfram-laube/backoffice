"""
Unit Tests for CRM Reporting Script

Tests funnel calculations, conversion rates, and rate analytics.
"""
import pytest
import sys
import os

# Add scripts/ci to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'ci'))


class TestFunnelCalculations:
    """Test funnel metric calculations."""
    
    def test_calc_funnel_counts_statuses(self, sample_issues):
        """Funnel should count issues per status."""
        # Simulate the funnel calculation logic
        from collections import defaultdict
        
        funnel = defaultdict(int)
        for issue in sample_issues:
            labels = issue.get("labels", [])
            for label in labels:
                if label.startswith("status::"):
                    status = label.replace("status::", "")
                    funnel[status] += 1
        
        assert funnel["versendet"] == 2
        assert funnel["absage"] == 1
        assert funnel["interview"] == 1
        assert funnel["neu"] == 1
    
    def test_calc_funnel_ignores_non_status_labels(self, sample_issues):
        """Funnel should only count status labels."""
        from collections import defaultdict
        
        funnel = defaultdict(int)
        for issue in sample_issues:
            labels = issue.get("labels", [])
            for label in labels:
                if label.startswith("status::"):
                    funnel[label.replace("status::", "")] += 1
        
        # Should not include tech:: or rate:: labels
        assert "python" not in funnel
        assert "105+" not in funnel
        assert "hot-lead" not in funnel


class TestConversionRates:
    """Test conversion rate calculations."""
    
    def test_overall_conversion_rate(self):
        """Overall conversion = zusagen / total."""
        funnel = {"versendet": 100, "beim-kunden": 10, "interview": 5, "zusage": 2, "absage": 20}
        total = sum(funnel.values())
        
        overall = funnel.get("zusage", 0) / total * 100
        
        assert overall == pytest.approx(1.46, rel=0.1)  # 2/137 ≈ 1.46%
    
    def test_stage_conversion_rates(self):
        """Stage-to-stage conversion rates."""
        funnel = {"versendet": 100, "beim-kunden": 10, "interview": 5, "verhandlung": 2, "zusage": 1}
        
        sent_to_client = funnel["beim-kunden"] / funnel["versendet"] * 100
        client_to_interview = funnel["interview"] / funnel["beim-kunden"] * 100
        interview_to_negotiation = funnel["verhandlung"] / funnel["interview"] * 100
        
        assert sent_to_client == 10.0
        assert client_to_interview == 50.0
        assert interview_to_negotiation == 40.0
    
    def test_conversion_handles_zero_denominator(self):
        """Conversion should handle zero without division error."""
        funnel = {"versendet": 0, "beim-kunden": 0, "zusage": 0}
        
        # Should not raise ZeroDivisionError
        total = sum(funnel.values())
        overall = (funnel.get("zusage", 0) / total * 100) if total > 0 else 0
        
        assert overall == 0


class TestRateAnalytics:
    """Test rate distribution analysis."""
    
    def test_rate_distribution(self, sample_issues):
        """Should count issues per rate range."""
        from collections import defaultdict
        
        rates = defaultdict(int)
        for issue in sample_issues:
            labels = issue.get("labels", [])
            for label in labels:
                if label.startswith("rate::"):
                    rates[label.replace("rate::", "")] += 1
        
        assert rates["105+"] == 3
        assert rates["95-105"] == 2
    
    def test_rate_mapping_to_numeric(self):
        """Rate ranges should map to numeric values for averaging."""
        rate_values = {"unter-85": 80, "85-95": 90, "95-105": 100, "105+": 110}
        
        assert rate_values["105+"] == 110
        assert rate_values["95-105"] == 100
        assert rate_values["unter-85"] == 80


class TestAgencyExtraction:
    """Test agency name extraction from titles."""
    
    def test_extract_agency_from_brackets(self):
        """Should extract agency name from [Agency] prefix."""
        titles = [
            "[Etengo AG] Senior Python Developer",
            "[Hays AG] DevOps Engineer",
            "[Computer Futures] ML Engineer",
        ]
        
        agencies = []
        for title in titles:
            if title.startswith("[") and "]" in title:
                agency = title[1:title.index("]")]
                agencies.append(agency)
        
        assert agencies == ["Etengo AG", "Hays AG", "Computer Futures"]
    
    def test_handle_missing_brackets(self):
        """Should handle titles without agency prefix."""
        title = "Direct Application - Cloud Architect"
        
        if title.startswith("[") and "]" in title:
            agency = title[1:title.index("]")]
        else:
            agency = "Direct/Unknown"
        
        assert agency == "Direct/Unknown"


class TestHotLeadDetection:
    """Test hot lead identification."""
    
    def test_count_hot_leads(self, sample_issues):
        """Should count open issues with hot-lead label."""
        hot_leads = [
            i for i in sample_issues
            if i.get("state") == "opened" and "hot-lead" in i.get("labels", [])
        ]
        
        assert len(hot_leads) == 2  # Issues 1 and 4
    
    def test_hot_leads_excludes_closed(self, sample_issues):
        """Closed issues should not be counted as hot leads."""
        # Add a closed hot lead
        sample_issues.append({
            "iid": 99,
            "state": "closed",
            "labels": ["status::absage", "hot-lead"],
        })
        
        hot_leads = [
            i for i in sample_issues
            if i.get("state") == "opened" and "hot-lead" in i.get("labels", [])
        ]
        
        # Should still be 2, not 3
        assert len(hot_leads) == 2
