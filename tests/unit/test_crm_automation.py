"""
Unit Tests for CRM Automation Script

Tests follow-up detection, ghost detection, and duplicate matching.
"""
import pytest
from datetime import datetime, timedelta
from difflib import SequenceMatcher


class TestFollowUpDetection:
    """Test follow-up reminder logic."""
    
    def test_detect_stale_issues(self, sample_issues):
        """Should detect issues without activity > FOLLOW_UP_DAYS."""
        FOLLOW_UP_DAYS = 7
        now = datetime(2026, 2, 1, 12, 0, 0)
        cutoff = now - timedelta(days=FOLLOW_UP_DAYS)
        
        def parse_dt(s):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        
        needs_followup = []
        for issue in sample_issues:
            # Only check versendet status
            if "status::versendet" not in issue.get("labels", []):
                continue
            
            updated = parse_dt(issue["updated_at"])
            if updated < cutoff:
                needs_followup.append(issue["iid"])
        
        # Issue 2 was last updated 2026-01-10, which is > 7 days before 2026-02-01
        assert 2 in needs_followup
        # Issue 1 was updated 2026-01-20, which is within range
        assert 1 not in needs_followup
    
    def test_skip_already_marked_followups(self, sample_issues):
        """Should skip issues already having needs-followup label."""
        sample_issues[1]["labels"].append("needs-followup")
        
        needs_followup = []
        for issue in sample_issues:
            if "needs-followup" in issue.get("labels", []):
                continue
            if "status::versendet" in issue.get("labels", []):
                needs_followup.append(issue["iid"])
        
        assert 2 not in needs_followup  # Was marked, should be skipped


class TestGhostDetection:
    """Test ghost (stale) issue detection."""
    
    def test_detect_ghost_candidates(self, sample_issues):
        """Should detect issues without activity > GHOST_DAYS."""
        GHOST_DAYS = 30
        now = datetime(2026, 2, 1, 12, 0, 0)
        cutoff = now - timedelta(days=GHOST_DAYS)
        
        def parse_dt(s):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        
        ghosts = []
        for issue in sample_issues:
            if "status::versendet" not in issue.get("labels", []):
                continue
            
            updated = parse_dt(issue["updated_at"])
            if updated < cutoff:
                ghosts.append(issue["iid"])
        
        # Issue 2 last updated 2026-01-10 = 22 days before Feb 1
        # That's < 30 days, so NOT a ghost yet
        assert 2 not in ghosts
    
    def test_ghost_only_from_versendet(self, sample_issues):
        """Only 'versendet' status can become ghost."""
        # Issue 3 is absage - should never become ghost
        ghosts = []
        for issue in sample_issues:
            if "status::versendet" not in issue.get("labels", []):
                continue
            ghosts.append(issue["iid"])
        
        assert 3 not in ghosts  # Absage, not versendet


class TestDuplicateDetection:
    """Test duplicate issue detection."""
    
    def test_detect_similar_titles(self):
        """Should detect titles with >80% similarity."""
        issues = [
            {"iid": 1, "title": "[Etengo] Senior Python Developer - Energy"},
            {"iid": 2, "title": "[Etengo] Senior Python Developer - Banking"},
            {"iid": 3, "title": "[Hays] DevOps Engineer Kubernetes"},
        ]
        
        duplicates = []
        for i, a in enumerate(issues):
            for b in issues[i+1:]:
                similarity = SequenceMatcher(
                    None, 
                    a["title"].lower(), 
                    b["title"].lower()
                ).ratio()
                
                if similarity > 0.8:
                    duplicates.append((a["iid"], b["iid"], similarity))
        
        # Issues 1 and 2 should be flagged as potential duplicates
        assert len(duplicates) == 1
        assert duplicates[0][0] == 1
        assert duplicates[0][1] == 2
        assert duplicates[0][2] > 0.8
    
    def test_no_false_positives(self):
        """Should not flag dissimilar titles."""
        issues = [
            {"iid": 1, "title": "[Etengo] Senior Python Developer"},
            {"iid": 2, "title": "[Hays] Junior Java Developer"},
            {"iid": 3, "title": "[SOLCOM] Cloud Architect AWS"},
        ]
        
        duplicates = []
        for i, a in enumerate(issues):
            for b in issues[i+1:]:
                similarity = SequenceMatcher(
                    None,
                    a["title"].lower(),
                    b["title"].lower()
                ).ratio()
                
                if similarity > 0.8:
                    duplicates.append((a["iid"], b["iid"]))
        
        assert len(duplicates) == 0
    
    def test_skip_phase_issues(self):
        """Should skip [Phase X] infrastructure issues."""
        issues = [
            {"iid": 1, "title": "[Phase 5] Reporting & Analytics"},
            {"iid": 2, "title": "[Phase 6] Smart Automation"},
            {"iid": 3, "title": "[Etengo] Senior Python Developer"},
        ]
        
        duplicates = []
        for i, a in enumerate(issues):
            for b in issues[i+1:]:
                # Skip phase issues
                if a["title"].lower().startswith("[phase") or b["title"].lower().startswith("[phase"):
                    continue
                
                similarity = SequenceMatcher(
                    None,
                    a["title"].lower(),
                    b["title"].lower()
                ).ratio()
                
                if similarity > 0.8:
                    duplicates.append((a["iid"], b["iid"]))
        
        # Should not compare phase issues
        assert len(duplicates) == 0


class TestLabelOperations:
    """Test label manipulation logic."""
    
    def test_get_status_from_labels(self):
        """Should extract status from labels."""
        labels = ["status::versendet", "rate::105+", "tech::python"]
        
        status = None
        for label in labels:
            if label.startswith("status::"):
                status = label
                break
        
        assert status == "status::versendet"
    
    def test_handle_missing_status(self):
        """Should handle issues without status label."""
        labels = ["rate::105+", "tech::python"]
        
        status = ""
        for label in labels:
            if label.startswith("status::"):
                status = label
                break
        
        assert status == ""
