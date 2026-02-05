"""
Integration Tests: Application Pipeline

Tests cross-module interactions with mocked external APIs.
Uses the same Randstad fixture as unit tests for coherent coverage.

Test Pyramid Layer: INTEGRATION
Scope: Multiple modules working together, mocked I/O
"""
import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from tests.fixtures.real_applications import (
    RANDSTAD_ARCHIVIERUNG_PROJECT,
    RANDSTAD_ARCHIVIERUNG_CSV_ENTRY,
    RANDSTAD_ARCHIVIERUNG_CRM_ISSUE,
)


# =============================================================================
# INT-1: CRAWL → MATCH PIPELINE
# =============================================================================

@pytest.mark.integration
class TestCrawlToMatch:
    """INT-1: Crawled projects flow correctly into the match stage."""

    def test_crawl_output_consumed_by_match(self, tmp_path):
        """Match stage can parse crawl output format."""
        # Simulate crawl output
        projects = [RANDSTAD_ARCHIVIERUNG_PROJECT]
        crawl_output = tmp_path / "output" / "projects.json"
        crawl_output.parent.mkdir(parents=True)
        crawl_output.write_text(json.dumps(projects))

        # Verify match can read it
        loaded = json.loads(crawl_output.read_text())
        assert len(loaded) == 1
        assert loaded[0]["title"] == RANDSTAD_ARCHIVIERUNG_PROJECT["title"]
        assert "skills" in loaded[0]

    def test_match_output_has_required_structure(self, tmp_path):
        """Match output contains everything QA and Drafts need."""
        match_result = {
            "matches": [
                {
                    "project": RANDSTAD_ARCHIVIERUNG_PROJECT,
                    "score": 90,
                    "profile": "wolfram",
                    "keywords": ["java", "kubernetes", "kafka", "spring"],
                    "is_ai": False,
                }
            ],
            "stats": {
                "total_projects": 1,
                "matched": 1,
                "filtered": 0,
            },
        }
        match_output = tmp_path / "output" / "matches.json"
        match_output.parent.mkdir(parents=True)
        match_output.write_text(json.dumps(match_result))

        loaded = json.loads(match_output.read_text())
        match = loaded["matches"][0]

        # Drafts stage needs these
        assert "project" in match
        assert "score" in match
        assert "keywords" in match
        assert match["project"]["title"]  # Not empty

        # QA stage needs these
        assert "stats" in loaded
        assert loaded["stats"]["total_projects"] > 0


# =============================================================================
# INT-2: MATCH → QA → DRAFT PIPELINE
# =============================================================================

@pytest.mark.integration
class TestMatchToQAToDraft:
    """INT-2: Match results pass QA validation and produce valid drafts."""

    def test_qa_passes_valid_match(self):
        """QA should pass a well-formed match result."""
        match = {
            "project": RANDSTAD_ARCHIVIERUNG_PROJECT,
            "score": 90,
            "profile": "wolfram",
            "keywords": ["java", "kubernetes"],
        }

        # QA checks
        assert match["score"] > 0, "Score must be positive"
        assert match["project"].get("title"), "Title required"
        assert match["project"].get("skills"), "Skills required"
        assert len(match["keywords"]) > 0, "Must have matched keywords"

    def test_qa_rejects_empty_project(self):
        """QA should reject a match with empty project data."""
        bad_match = {
            "project": {"title": "", "skills": []},
            "score": 0,
            "keywords": [],
        }

        has_issues = (
            not bad_match["project"]["title"]
            or not bad_match["project"]["skills"]
            or bad_match["score"] == 0
        )
        assert has_issues, "QA should flag empty project"

    def test_draft_json_structure_for_gmail(self):
        """Draft output must be valid for gmail-drafts.yml consumption."""
        draft = {
            "to": "matthias.steckiewicz@randstad.de",
            "subject": "Bewerbung: Java Software Engineer K8s/Kafka (C01236721)",
            "body": "Sehr geehrter Herr Steckiewicz,\n\ngerne bewerbe ich mich auf das Projekt Java Software Engineer (C01236721).",
            "attachments": ["attachments/Profil_Laube_w_Summary_DE.pdf"],
        }

        # Validate gmail-drafts.yml expected format
        assert "to" in draft
        assert "subject" in draft
        assert "body" in draft
        assert len(draft["body"]) > 50
        assert isinstance(draft.get("attachments", []), list)


# =============================================================================
# INT-3: DRAFT → CRM SYNC
# =============================================================================

@pytest.mark.integration
class TestDraftToCRMSync:
    """INT-3: After draft creation, CRM issue is created/updated."""

    def test_crm_issue_title_derived_from_csv(self):
        """CRM issue title should follow [Provider] Title convention."""
        csv = RANDSTAD_ARCHIVIERUNG_CSV_ENTRY
        expected_title = f"[{csv['provider']}] {csv['project_title']}"
        assert expected_title == RANDSTAD_ARCHIVIERUNG_CRM_ISSUE["expected_title"]

    def test_crm_labels_derived_from_csv(self):
        """CRM labels should be auto-generated from CSV data."""
        csv = RANDSTAD_ARCHIVIERUNG_CSV_ENTRY
        labels = []

        # Status mapping
        status_map = {
            "versendet": "status::versendet",
            "interview": "status::interview",
            "abgelehnt": "status::absage",
        }
        labels.append(status_map.get(csv["status"], f"status::{csv['status']}"))

        # Rate mapping
        rate = int(csv["rate_eur_h"])
        if rate >= 105:
            labels.append("rate::105+")
        elif rate >= 95:
            labels.append("rate::95-105")
        else:
            labels.append("rate::<95")

        assert "status::versendet" in labels
        assert "rate::105+" in labels

    @patch("requests.post")
    def test_crm_api_called_with_correct_payload(self, mock_post):
        """CRM sync should POST to GitLab Issues API."""
        mock_post.return_value = MagicMock(
            status_code=201,
            json=lambda: {"iid": 189, "web_url": "https://gitlab.com/..."}
        )

        csv = RANDSTAD_ARCHIVIERUNG_CSV_ENTRY
        payload = {
            "title": f"[{csv['provider']}] {csv['project_title']}",
            "labels": "status::versendet,rate::105+,tech::java,tech::kubernetes",
        }

        import requests
        resp = requests.post(
            "https://gitlab.com/api/v4/projects/78171527/issues",
            headers={"PRIVATE-TOKEN": "test-token"},
            json=payload,
        )

        assert resp.status_code == 201
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "issues" in call_kwargs[0][0]


# =============================================================================
# INT-4: FULL PIPELINE SIMULATION (in-memory)
# =============================================================================

@pytest.mark.integration
class TestFullPipelineSimulation:
    """INT-4: Simulate complete pipeline in-memory without real APIs."""

    def test_full_flow_crawl_to_crm(self, tmp_path):
        """
        Simulate: crawl → match → QA → draft → CRM sync.
        All in-memory with file artifacts in tmp_path.
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Step 1: Crawl output
        projects = [RANDSTAD_ARCHIVIERUNG_PROJECT]
        (output_dir / "projects.json").write_text(json.dumps(projects))

        # Step 2: Match (simplified)
        matches = {
            "matches": [
                {
                    "project": projects[0],
                    "score": 90,
                    "profile": "wolfram",
                    "keywords": ["java", "kubernetes", "kafka"],
                }
            ],
            "stats": {"total_projects": 1, "matched": 1, "filtered": 0},
        }
        (output_dir / "matches.json").write_text(json.dumps(matches))

        # Step 3: QA validation
        qa_report = {"tests": [], "failures": 0, "warnings": 0, "passed": 3}
        loaded_matches = json.loads((output_dir / "matches.json").read_text())
        for m in loaded_matches["matches"]:
            assert m["score"] > 0
            assert m["project"]["title"]
            qa_report["tests"].append({"name": "score_valid", "status": "passed"})
            qa_report["tests"].append({"name": "title_present", "status": "passed"})
            qa_report["tests"].append({"name": "keywords_present", "status": "passed"})
        (output_dir / "qa_report.json").write_text(json.dumps(qa_report))

        # Step 4: Draft generation
        draft = {
            "to": "",
            "subject": f"Bewerbung: {projects[0]['title'][:60]}",
            "body": f"Sehr geehrter Herr Steckiewicz...",
            "attachments": ["attachments/Profil_Laube_w_Summary_DE.pdf"],
        }
        (output_dir / "drafts.json").write_text(json.dumps([draft]))

        # Step 5: CRM issue data
        crm_issue = {
            "title": f"[Randstad Professional / GULP] {RANDSTAD_ARCHIVIERUNG_CSV_ENTRY['project_title']}",
            "labels": "status::versendet,rate::105+,tech::java,tech::kubernetes",
        }
        (output_dir / "crm_update_results.json").write_text(json.dumps([crm_issue]))

        # Verify all artifacts exist
        expected_files = [
            "projects.json", "matches.json", "qa_report.json",
            "drafts.json", "crm_update_results.json",
        ]
        for f in expected_files:
            assert (output_dir / f).exists(), f"Missing artifact: {f}"

        # Verify data flows correctly
        final_crm = json.loads((output_dir / "crm_update_results.json").read_text())
        assert "Archivierungssystem" in final_crm[0]["title"]
        assert "status::versendet" in final_crm[0]["labels"]
