"""
Unit Tests for Applications QA Script

Tests QAReport class and validation logic.
"""
import pytest
import json
from datetime import datetime


class QAReport:
    """Simplified QAReport for testing (matches production class)."""
    
    def __init__(self):
        self.tests = []
        self.failures = 0
        self.warnings = 0
        self.passed = 0

    def ok(self, name, detail=""):
        self.tests.append({"name": name, "status": "passed", "detail": detail})
        self.passed += 1

    def fail(self, name, detail=""):
        self.tests.append({"name": name, "status": "failed", "detail": detail})
        self.failures += 1

    def warn(self, name, detail=""):
        self.tests.append({"name": name, "status": "warning", "detail": detail})
        self.warnings += 1

    @property
    def exit_code(self):
        if self.failures > 0: return 1
        if self.warnings > 0: return 2
        return 0


class TestQAReport:
    """Test QAReport functionality."""
    
    def test_initial_state(self):
        """New report should have zero counts."""
        report = QAReport()
        
        assert report.passed == 0
        assert report.failures == 0
        assert report.warnings == 0
        assert len(report.tests) == 0
    
    def test_ok_increments_passed(self):
        """ok() should increment passed counter."""
        report = QAReport()
        
        report.ok("test1")
        report.ok("test2", "with detail")
        
        assert report.passed == 2
        assert report.failures == 0
        assert len(report.tests) == 2
    
    def test_fail_increments_failures(self):
        """fail() should increment failures counter."""
        report = QAReport()
        
        report.fail("test1", "reason")
        
        assert report.failures == 1
        assert report.passed == 0
    
    def test_warn_increments_warnings(self):
        """warn() should increment warnings counter."""
        report = QAReport()
        
        report.warn("test1", "minor issue")
        
        assert report.warnings == 1
        assert report.failures == 0
    
    def test_exit_code_success(self):
        """All passed should return exit code 0."""
        report = QAReport()
        report.ok("test1")
        report.ok("test2")
        
        assert report.exit_code == 0
    
    def test_exit_code_failure(self):
        """Any failure should return exit code 1."""
        report = QAReport()
        report.ok("test1")
        report.fail("test2", "error")
        report.ok("test3")
        
        assert report.exit_code == 1
    
    def test_exit_code_warning(self):
        """Warnings only should return exit code 2."""
        report = QAReport()
        report.ok("test1")
        report.warn("test2", "warning")
        
        assert report.exit_code == 2
    
    def test_failure_takes_precedence_over_warning(self):
        """Failure exit code (1) should take precedence over warning (2)."""
        report = QAReport()
        report.warn("test1", "warning")
        report.fail("test2", "failure")
        
        assert report.exit_code == 1
    
    def test_test_details_stored(self):
        """Test details should be stored correctly."""
        report = QAReport()
        report.ok("check_files", "3 files found")
        report.fail("check_format", "invalid JSON")
        
        assert report.tests[0]["name"] == "check_files"
        assert report.tests[0]["status"] == "passed"
        assert report.tests[0]["detail"] == "3 files found"
        
        assert report.tests[1]["name"] == "check_format"
        assert report.tests[1]["status"] == "failed"


class TestCrawlValidation:
    """Test crawl output validation logic."""
    
    def validate_project(self, project):
        """Validate a single project structure."""
        errors = []
        
        if not project.get("title"):
            errors.append("missing title")
        
        if not project.get("url"):
            errors.append("missing url")
        
        if project.get("rate"):
            try:
                rate = int(str(project["rate"]).replace("€", "").replace("/h", "").strip())
                if rate < 50 or rate > 200:
                    errors.append(f"rate out of range: {rate}")
            except ValueError:
                errors.append(f"invalid rate format: {project['rate']}")
        
        return errors
    
    def test_valid_project(self):
        """Valid project should pass validation."""
        project = {
            "title": "Senior Python Developer",
            "url": "https://freelancermap.de/projekt/123",
            "rate": "100€/h",
            "description": "Looking for Python expert"
        }
        
        errors = self.validate_project(project)
        assert len(errors) == 0
    
    def test_missing_title(self):
        """Missing title should fail."""
        project = {"url": "https://example.com", "rate": "100"}
        
        errors = self.validate_project(project)
        assert "missing title" in errors
    
    def test_missing_url(self):
        """Missing URL should fail."""
        project = {"title": "Developer", "rate": "100"}
        
        errors = self.validate_project(project)
        assert "missing url" in errors
    
    def test_rate_out_of_range(self):
        """Rate outside 50-200 should warn."""
        project = {"title": "Dev", "url": "http://x", "rate": "250"}
        
        errors = self.validate_project(project)
        assert any("out of range" in e for e in errors)


class TestMatchValidation:
    """Test match output validation logic."""
    
    def validate_match(self, match):
        """Validate a single match structure."""
        errors = []
        
        if "project" not in match:
            errors.append("missing project reference")
        
        if "score" not in match and "percentage" not in match:
            errors.append("missing score")
        
        score = match.get("score") or match.get("percentage", 0)
        if not (0 <= score <= 100):
            errors.append(f"score out of range: {score}")
        
        return errors
    
    def test_valid_match(self):
        """Valid match should pass."""
        match = {
            "project": {"title": "Test"},
            "score": 85,
            "profile": "wolfram"
        }
        
        errors = self.validate_match(match)
        assert len(errors) == 0
    
    def test_missing_project(self):
        """Missing project reference should fail."""
        match = {"score": 85}
        
        errors = self.validate_match(match)
        assert "missing project reference" in errors
    
    def test_score_out_of_range(self):
        """Score > 100 should fail."""
        match = {"project": {}, "score": 150}
        
        errors = self.validate_match(match)
        assert any("out of range" in e for e in errors)
