"""
Unit Tests for CRM Integrity Check Script

Tests data validation and anomaly detection.
"""
import pytest
from collections import Counter


class TestLabelValidation:
    """Test label consistency checks."""
    
    VALID_STATUSES = {
        "status::neu", "status::versendet", "status::beim-kunden",
        "status::interview", "status::verhandlung", "status::zusage",
        "status::absage", "status::ghost"
    }
    
    VALID_RATES = {"rate::unter-85", "rate::85-95", "rate::95-105", "rate::105+"}
    
    def get_labels(self, issue):
        """Extract label names from issue."""
        return [l["name"] if isinstance(l, dict) else l for l in issue.get("labels", [])]
    
    def validate_status_labels(self, issue):
        """Check that issue has exactly one status label."""
        labels = self.get_labels(issue)
        statuses = [l for l in labels if l.startswith("status::")]
        
        if len(statuses) == 0:
            return "missing_status"
        elif len(statuses) > 1:
            return "multiple_statuses"
        elif statuses[0] not in self.VALID_STATUSES:
            return "invalid_status"
        else:
            return "ok"
    
    def test_valid_single_status(self):
        """Issue with one valid status should pass."""
        issue = {"labels": ["status::versendet", "rate::105+"]}
        
        result = self.validate_status_labels(issue)
        assert result == "ok"
    
    def test_missing_status(self):
        """Issue without status should fail."""
        issue = {"labels": ["rate::105+", "tech::python"]}
        
        result = self.validate_status_labels(issue)
        assert result == "missing_status"
    
    def test_multiple_statuses(self):
        """Issue with multiple statuses should fail."""
        issue = {"labels": ["status::versendet", "status::interview"]}
        
        result = self.validate_status_labels(issue)
        assert result == "multiple_statuses"
    
    def test_invalid_status(self):
        """Issue with unknown status should fail."""
        issue = {"labels": ["status::unknown"]}
        
        result = self.validate_status_labels(issue)
        assert result == "invalid_status"


class TestTitleValidation:
    """Test issue title format validation."""
    
    def validate_title(self, title):
        """Validate title format: [Agency] Description."""
        errors = []
        
        if not title:
            errors.append("empty_title")
            return errors
        
        # Check for agency prefix
        if not (title.startswith("[") and "]" in title):
            errors.append("missing_agency_prefix")
        
        # Check minimum length
        if len(title) < 15:
            errors.append("title_too_short")
        
        # Check for [Phase X] pattern (infra issues, allowed)
        if title.lower().startswith("[phase"):
            return []  # Infrastructure issues are exempt
        
        return errors
    
    def test_valid_title(self):
        """Standard title should pass."""
        title = "[Etengo AG] Senior Python Developer - Energy Sector"
        
        errors = self.validate_title(title)
        assert len(errors) == 0
    
    def test_missing_agency(self):
        """Title without agency prefix should warn."""
        title = "Senior Python Developer"
        
        errors = self.validate_title(title)
        assert "missing_agency_prefix" in errors
    
    def test_short_title(self):
        """Very short title should warn."""
        title = "[X] Dev"
        
        errors = self.validate_title(title)
        assert "title_too_short" in errors
    
    def test_phase_title_exempt(self):
        """[Phase X] titles should be exempt."""
        title = "[Phase 5] Reporting & Analytics"
        
        errors = self.validate_title(title)
        assert len(errors) == 0


class TestDuplicateDetection:
    """Test duplicate issue detection."""
    
    def find_duplicates(self, issues):
        """Find issues with identical titles."""
        title_counts = Counter(i.get("title", "").lower() for i in issues)
        duplicates = [t for t, count in title_counts.items() if count > 1 and t]
        return duplicates
    
    def test_no_duplicates(self):
        """Unique titles should return empty list."""
        issues = [
            {"title": "Python Developer"},
            {"title": "Java Developer"},
            {"title": "DevOps Engineer"}
        ]
        
        dupes = self.find_duplicates(issues)
        assert len(dupes) == 0
    
    def test_detect_duplicates(self):
        """Identical titles should be detected."""
        issues = [
            {"title": "Python Developer"},
            {"title": "Python Developer"},  # Duplicate
            {"title": "Java Developer"}
        ]
        
        dupes = self.find_duplicates(issues)
        assert "python developer" in dupes
    
    def test_case_insensitive(self):
        """Duplicate detection should be case-insensitive."""
        issues = [
            {"title": "Python Developer"},
            {"title": "PYTHON DEVELOPER"},  # Same, different case
        ]
        
        dupes = self.find_duplicates(issues)
        assert len(dupes) == 1


class TestAnomalyDetection:
    """Test anomaly detection in CRM data."""
    
    def detect_rate_anomalies(self, issues):
        """Detect issues with unusual rate patterns."""
        anomalies = []
        
        for issue in issues:
            labels = [l["name"] if isinstance(l, dict) else l for l in issue.get("labels", [])]
            rates = [l for l in labels if l.startswith("rate::")]
            
            # Multiple rate labels
            if len(rates) > 1:
                anomalies.append({"iid": issue.get("iid"), "issue": "multiple_rates"})
            
            # No rate label on non-closed issue
            if len(rates) == 0:
                status = next((l for l in labels if l.startswith("status::")), "")
                if status not in ["status::absage", "status::ghost"]:
                    anomalies.append({"iid": issue.get("iid"), "issue": "missing_rate"})
        
        return anomalies
    
    def test_multiple_rates_detected(self):
        """Issue with multiple rate labels should be flagged."""
        issues = [
            {"iid": 1, "labels": ["status::versendet", "rate::105+", "rate::95-105"]}
        ]
        
        anomalies = self.detect_rate_anomalies(issues)
        assert len(anomalies) == 1
        assert anomalies[0]["issue"] == "multiple_rates"
    
    def test_missing_rate_on_active(self):
        """Active issue without rate should be flagged."""
        issues = [
            {"iid": 1, "labels": ["status::versendet"]}  # No rate
        ]
        
        anomalies = self.detect_rate_anomalies(issues)
        assert len(anomalies) == 1
        assert anomalies[0]["issue"] == "missing_rate"
    
    def test_missing_rate_ok_for_closed(self):
        """Closed issues can skip rate label."""
        issues = [
            {"iid": 1, "labels": ["status::absage"]}  # Closed, no rate OK
        ]
        
        anomalies = self.detect_rate_anomalies(issues)
        assert len(anomalies) == 0
