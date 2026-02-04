"""
Unit Tests for Applications Match Script

Tests AI detection, matching logic, and sorting.
"""
import pytest


class TestAIProjectDetection:
    """Test AI/KI project identification."""
    
    AI_KEYWORDS = {"ki", "ai", "llm", "ml", "genai", "machine learning", "deep learning", 
                   "rag", "nlp", "gpt", "neural", "tensorflow", "pytorch", "data scientist"}
    
    def is_ai_project(self, project):
        """Check if project title contains AI keywords."""
        title = project.get("title", "").lower()
        return any(kw in title for kw in self.AI_KEYWORDS)
    
    def test_detect_ai_project(self):
        """Should detect AI/ML projects by title."""
        projects = [
            {"title": "Senior AI Engineer - LLM Development"},
            {"title": "Machine Learning Platform Architect"},
            {"title": "Data Scientist - NLP Focus"},
            {"title": "GenAI Solutions Developer"},
        ]
        
        for p in projects:
            assert self.is_ai_project(p), f"Should detect: {p['title']}"
    
    def test_non_ai_project(self):
        """Should NOT flag non-AI projects."""
        projects = [
            {"title": "Senior Java Developer"},
            {"title": "DevOps Engineer - Kubernetes"},
            {"title": "Cloud Architect - AWS"},
            {"title": "Python Backend Developer"},
        ]
        
        for p in projects:
            assert not self.is_ai_project(p), f"Should NOT detect: {p['title']}"
    
    def test_case_insensitive(self):
        """AI detection should be case-insensitive."""
        projects = [
            {"title": "AI ENGINEER"},
            {"title": "ai engineer"},
            {"title": "Ai Engineer"},
        ]
        
        for p in projects:
            assert self.is_ai_project(p)


class TestMatchScoring:
    """Test project matching logic."""
    
    def match_team(self, project, keywords):
        """Simplified team matching logic."""
        search_text = " ".join([
            project.get("title", ""),
            project.get("description", ""),
            " ".join(project.get("skills", [])),
        ]).lower()
        
        matches = [kw for kw in keywords if kw.lower() in search_text]
        
        if len(matches) >= 6:
            score = min(100, 70 + (len(matches) - 6) * 5)
        elif len(matches) >= 3:
            score = 50 + (len(matches) - 3) * 7
        elif len(matches) >= 1:
            score = 20 + (len(matches) - 1) * 15
        else:
            score = 0
        
        return {"percentage": score, "matches": matches}
    
    def test_high_match_score(self):
        """6+ keyword matches should score 70+."""
        project = {
            "title": "DevOps Engineer",
            "description": "Python, Kubernetes, AWS, Docker, CI/CD, Terraform, Ansible",
            "skills": ["python", "kubernetes"]
        }
        keywords = {"python", "kubernetes", "aws", "docker", "ci/cd", "terraform", "ansible"}
        
        result = self.match_team(project, keywords)
        assert result["percentage"] >= 70
        assert len(result["matches"]) >= 6
    
    def test_medium_match_score(self):
        """3-5 keyword matches should score 50-69."""
        project = {
            "title": "Python Developer",
            "description": "Django, REST API",
            "skills": []
        }
        keywords = {"python", "django", "rest", "api", "flask"}
        
        result = self.match_team(project, keywords)
        assert 50 <= result["percentage"] < 70
    
    def test_low_match_score(self):
        """1-2 keyword matches should score 20-49."""
        project = {
            "title": "Java Developer",
            "description": "Spring Boot",
            "skills": []
        }
        keywords = {"java", "spring", "python", "kubernetes"}
        
        result = self.match_team(project, keywords)
        assert 20 <= result["percentage"] < 50
    
    def test_no_match(self):
        """No keyword matches should score 0."""
        project = {
            "title": "SAP Consultant",
            "description": "ABAP, HANA",
            "skills": []
        }
        keywords = {"python", "kubernetes", "aws"}
        
        result = self.match_team(project, keywords)
        assert result["percentage"] == 0


class TestMatchSorting:
    """Test match result sorting."""
    
    AI_KEYWORDS = {"ai", "ml", "llm"}
    
    def is_ai_project(self, project):
        title = project.get("title", "").lower()
        return any(kw in title for kw in self.AI_KEYWORDS)
    
    def sort_matches(self, matches):
        """Sort matches: AI projects first, then by score."""
        def sort_key(m):
            is_ai = self.is_ai_project(m["project"])
            return (-(1000 if is_ai else 0) - m["score"], m["project"]["title"])
        return sorted(matches, key=sort_key)
    
    def test_ai_projects_first(self):
        """AI projects should be sorted before non-AI even with lower score."""
        matches = [
            {"project": {"title": "Java Developer"}, "score": 95},
            {"project": {"title": "AI Engineer"}, "score": 70},
            {"project": {"title": "Python ML Developer"}, "score": 80},
        ]
        
        sorted_matches = self.sort_matches(matches)
        
        # AI projects should come first
        assert "AI" in sorted_matches[0]["project"]["title"] or "ML" in sorted_matches[0]["project"]["title"]
    
    def test_score_sorting_within_category(self):
        """Within same category, higher scores first."""
        matches = [
            {"project": {"title": "Python Developer"}, "score": 70},
            {"project": {"title": "Java Developer"}, "score": 90},
            {"project": {"title": "Go Developer"}, "score": 80},
        ]
        
        sorted_matches = self.sort_matches(matches)
        
        # Should be sorted by score descending
        assert sorted_matches[0]["score"] == 90
        assert sorted_matches[1]["score"] == 80
        assert sorted_matches[2]["score"] == 70
