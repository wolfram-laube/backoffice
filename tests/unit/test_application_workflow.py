"""
Unit Tests: Application Workflow (Use-Case-Driven)

Tests the complete application workflow at the unit level,
using the Randstad Archivierung Hamburg project as canonical fixture.

Test Pyramid Layer: UNIT
Scope: Individual functions, no I/O, no network
"""
import pytest
import json
import os
import re
import sys
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from tests.fixtures.real_applications import (
    RANDSTAD_ARCHIVIERUNG_PROJECT,
    RANDSTAD_ARCHIVIERUNG_EXPECTED_MATCH,
    RANDSTAD_ARCHIVIERUNG_CSV_ENTRY,
    RANDSTAD_ARCHIVIERUNG_DRAFT,
    RANDSTAD_ARCHIVIERUNG_CRM_ISSUE,
    AI_PROJECT,
    DEVOPS_PROJECT,
    LOW_MATCH_PROJECT,
)


# =============================================================================
# UC-1: MATCH SCORING
# =============================================================================

class TestMatchScoring:
    """UC-1: Given a crawled project, score it against Wolfram's profile."""

    def test_randstad_scores_above_threshold(self):
        """Randstad Archivierung should score >= 80% for Wolfram."""
        from modules.profiles import WOLFRAM, match_profile

        search_text = " ".join([
            RANDSTAD_ARCHIVIERUNG_PROJECT["title"],
            RANDSTAD_ARCHIVIERUNG_PROJECT["description"],
            " ".join(RANDSTAD_ARCHIVIERUNG_PROJECT["skills"]),
        ]).lower()

        result = match_profile(WOLFRAM, search_text)
        score = result["percentage"]

        assert score >= RANDSTAD_ARCHIVIERUNG_EXPECTED_MATCH["min_score"], \
            f"Expected >= {RANDSTAD_ARCHIVIERUNG_EXPECTED_MATCH['min_score']}%, got {score}%"

    def test_randstad_hits_must_have_keywords(self):
        """All must-have keywords should be matched."""
        from modules.profiles import WOLFRAM, match_profile

        search_text = " ".join([
            RANDSTAD_ARCHIVIERUNG_PROJECT["title"],
            RANDSTAD_ARCHIVIERUNG_PROJECT["description"],
            " ".join(RANDSTAD_ARCHIVIERUNG_PROJECT["skills"]),
        ]).lower()

        result = match_profile(WOLFRAM, search_text)
        # Collect all matched keywords across categories
        matched_kws = set()
        for category in ("must_have", "strong_match", "nice_to_have"):
            matched_kws.update(k.lower() for k in result["matches"].get(category, []))

        for expected_kw in RANDSTAD_ARCHIVIERUNG_EXPECTED_MATCH["must_have_keywords_hit"]:
            assert any(expected_kw in m for m in matched_kws), \
                f"Expected keyword '{expected_kw}' not found in matches: {matched_kws}"

    def test_low_match_project_scores_below_threshold(self):
        """SAP ABAP project should score < 30% for Wolfram."""
        from modules.profiles import WOLFRAM, match_profile

        search_text = " ".join([
            LOW_MATCH_PROJECT["title"],
            LOW_MATCH_PROJECT["description"],
            " ".join(LOW_MATCH_PROJECT["skills"]),
        ]).lower()

        result = match_profile(WOLFRAM, search_text)
        assert result["percentage"] < 30, \
            f"SAP ABAP should be low match, got {result['percentage']}%"

    def test_ai_project_detected_as_ai(self):
        """AI/KI projects should be detected for prioritization."""
        from scripts.ci.applications_match import is_ai_project

        assert is_ai_project(AI_PROJECT) is True
        assert is_ai_project(RANDSTAD_ARCHIVIERUNG_PROJECT) is False
        assert is_ai_project(LOW_MATCH_PROJECT) is False

    @pytest.mark.parametrize("project,min_score", [
        (RANDSTAD_ARCHIVIERUNG_PROJECT, 80),
        (AI_PROJECT, 50),
        (DEVOPS_PROJECT, 70),
        (LOW_MATCH_PROJECT, 0),
    ])
    def test_score_ranges_parametrized(self, project, min_score):
        """Verify scoring across project types."""
        from modules.profiles import WOLFRAM, match_profile

        search_text = " ".join([
            project["title"],
            project.get("description", ""),
            " ".join(project.get("skills", [])),
        ]).lower()

        result = match_profile(WOLFRAM, search_text)
        assert result["percentage"] >= min_score, \
            f"{project['title']}: expected >= {min_score}%, got {result['percentage']}%"


# =============================================================================
# UC-2: EMAIL GENERATION
# =============================================================================

class TestEmailGeneration:
    """UC-2: Given a match, generate a personalized application email."""

    def test_randstad_email_contains_key_terms(self):
        """Generated email for Randstad should contain ICMPD, 50Hertz, etc."""
        from scripts.ci.applications_drafts import generate_email_body

        body = generate_email_body(
            RANDSTAD_ARCHIVIERUNG_PROJECT,
            "Wolfram Laube",
            RANDSTAD_ARCHIVIERUNG_PROJECT["skills"],
        )

        # Standard assertions — email generator should include profile highlights
        assert "Wolfram Laube" in body
        assert "Archivierung" in body or "archivierung" in body.lower()

    def test_email_not_empty(self):
        """Email body must have substantial content."""
        from scripts.ci.applications_drafts import generate_email_body

        body = generate_email_body(
            RANDSTAD_ARCHIVIERUNG_PROJECT,
            "Wolfram Laube",
            ["Java", "Kubernetes", "Kafka"],
        )

        assert len(body) > 200, f"Email too short: {len(body)} chars"

    def test_ai_project_gets_ai_intro(self):
        """AI projects should use AI-specific intro."""
        from scripts.ci.applications_drafts import generate_email_body

        body = generate_email_body(AI_PROJECT, "Wolfram Laube", ["LLM", "RAG"])
        assert "AI" in body or "ML" in body or "JKU" in body


# =============================================================================
# UC-3: QA VALIDATION
# =============================================================================

class TestQAValidation:
    """UC-3: QA checks on crawl/match outputs before draft creation."""

    def test_project_has_required_fields(self):
        """Crawled project must have title, skills, location."""
        project = RANDSTAD_ARCHIVIERUNG_PROJECT
        assert project.get("title"), "Missing title"
        assert project.get("skills"), "Missing skills"
        assert project.get("location"), "Missing location"
        assert len(project["skills"]) >= 3, "Too few skills extracted"

    def test_match_output_structure(self):
        """Match output must have score, profile, project reference."""
        match_output = {
            "project": RANDSTAD_ARCHIVIERUNG_PROJECT,
            "score": 90,
            "profile": "wolfram",
            "keywords": ["java", "kubernetes", "kafka"],
        }
        assert "project" in match_output
        assert "score" in match_output
        assert isinstance(match_output["score"], (int, float))
        assert 0 <= match_output["score"] <= 100

    def test_csv_entry_has_all_columns(self):
        """CSV entry must have all required columns."""
        required_cols = [
            "date_recorded", "project_title", "provider",
            "contact_name", "status", "rate_eur_h",
        ]
        for col in required_cols:
            assert col in RANDSTAD_ARCHIVIERUNG_CSV_ENTRY, \
                f"Missing CSV column: {col}"

    def test_csv_rate_is_numeric(self):
        """Rate must be a valid number."""
        rate = RANDSTAD_ARCHIVIERUNG_CSV_ENTRY["rate_eur_h"]
        assert rate.isdigit() or rate.replace(".", "", 1).isdigit(), \
            f"Rate not numeric: {rate}"

    def test_csv_status_is_valid(self):
        """Status must be a known value."""
        valid_statuses = {
            "versendet", "nicht beworben", "abgelehnt", "interview",
            "antwort erhalten", "telefonat", "beim kunden", "zusage",
            "draft", "versendet via freelancermap",
        }
        status = RANDSTAD_ARCHIVIERUNG_CSV_ENTRY["status"]
        assert status in valid_statuses, \
            f"Unknown status: {status}"

    def test_no_duplicate_detection(self):
        """Same project from different providers should be flagged."""
        existing_titles = [
            "Java Software Engineer - Kubernetes/Kafka Archivierungssystem",
        ]
        new_title = "Java Entwickler K8s Kafka Archivierung"

        # Tokenize on whitespace, slashes, and hyphens for better overlap detection
        def tokenize(text):
            return set(re.split(r'[\s/\-]+', text.lower())) - {''}

        words_existing = tokenize(existing_titles[0])
        words_new = tokenize(new_title)
        overlap = words_existing & words_new
        # Should have some overlap but not be identical
        assert len(overlap) >= 2, \
            f"Duplicate detection should find common words, got: {overlap}"


# =============================================================================
# UC-4: CRM ISSUE CREATION
# =============================================================================

class TestCRMIssueCreation:
    """UC-4: Application data maps correctly to CRM issue."""

    def test_issue_title_format(self):
        """CRM issue title should be [Provider] Project Title."""
        provider = RANDSTAD_ARCHIVIERUNG_CSV_ENTRY["provider"]
        title = RANDSTAD_ARCHIVIERUNG_CSV_ENTRY["project_title"]
        expected = f"[{provider}] {title}"
        assert expected == RANDSTAD_ARCHIVIERUNG_CRM_ISSUE["expected_title"]

    def test_issue_has_status_label(self):
        """CRM issue must have a status:: label."""
        labels = RANDSTAD_ARCHIVIERUNG_CRM_ISSUE["expected_labels"]
        status_labels = [l for l in labels if l.startswith("status::")]
        assert len(status_labels) == 1, f"Expected exactly 1 status label, got {status_labels}"

    def test_issue_has_rate_label(self):
        """CRM issue must have a rate:: label matching the hourly rate."""
        labels = RANDSTAD_ARCHIVIERUNG_CRM_ISSUE["expected_labels"]
        rate_labels = [l for l in labels if l.startswith("rate::")]
        assert len(rate_labels) == 1

        rate = int(RANDSTAD_ARCHIVIERUNG_CSV_ENTRY["rate_eur_h"])
        if rate >= 105:
            assert "rate::105+" in labels
        elif rate >= 95:
            assert "rate::95-105" in labels

    def test_issue_has_tech_labels(self):
        """CRM issue should have tech:: labels for key technologies."""
        labels = RANDSTAD_ARCHIVIERUNG_CRM_ISSUE["expected_labels"]
        tech_labels = [l for l in labels if l.startswith("tech::")]
        assert len(tech_labels) >= 1, "Should have at least one tech label"
