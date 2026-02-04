"""
Unit Tests for modules/profiles/

Tests:
- Profile/Team model creation
- YAML loading
- Keyword matching
- Legacy compatibility
"""

import pytest
from pathlib import Path


class TestProfileModels:
    """Test Profile and Team dataclasses."""
    
    def test_rate_config_from_dict(self):
        """RateConfig should parse dict correctly."""
        from modules.profiles.models import RateConfig
        
        rate = RateConfig.from_dict({"min": 80, "max": 130, "preferred": 100})
        assert rate.min == 80
        assert rate.max == 130
        assert rate.preferred == 100
    
    def test_rate_config_from_single_value(self):
        """RateConfig should handle single value."""
        from modules.profiles.models import RateConfig
        
        rate = RateConfig.from_dict(105)
        assert rate.preferred == 105
        assert rate.min == 90  # 105 - 15
        assert rate.max == 120  # 105 + 15
    
    def test_keyword_config_from_dict(self):
        """KeywordConfig should parse lists to sets."""
        from modules.profiles.models import KeywordConfig
        
        kw = KeywordConfig.from_dict({
            "must_have": ["python", "kubernetes"],
            "strong_match": ["aws"],
            "nice_to_have": ["linux"],
            "exclude": ["junior"]
        })
        
        assert "python" in kw.must_have
        assert "kubernetes" in kw.must_have
        assert "aws" in kw.strong_match
        assert "linux" in kw.nice_to_have
        assert "junior" in kw.exclude
    
    def test_profile_from_dict(self):
        """Profile should parse full config dict."""
        from modules.profiles.models import Profile
        
        data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+1234567890",
            "rate": {"min": 90, "max": 120, "preferred": 105},
            "attachments": {"cv_de": "cv.pdf"},
            "signature": "Best regards",
            "constraints": {"remote_only": True, "languages": ["DE", "EN"]},
            "keywords": {
                "must_have": ["python"],
                "exclude": ["junior"]
            }
        }
        
        profile = Profile.from_dict("test", data)
        
        assert profile.key == "test"
        assert profile.name == "Test User"
        assert profile.email == "test@example.com"
        assert profile.rate.preferred == 105
        assert "python" in profile.keywords.must_have
        assert profile.constraints.remote_only is True
    
    def test_profile_legacy_properties(self):
        """Profile should expose legacy properties."""
        from modules.profiles.models import Profile
        
        data = {
            "name": "Test",
            "email": "test@example.com",
            "phone": "123",
            "rate": {"min": 90, "max": 120, "preferred": 105},
            "attachments": {"cv_de": "cv_de.pdf", "cv_en": "cv_en.pdf"},
            "keywords": {"must_have": ["python"]}
        }
        
        profile = Profile.from_dict("test", data)
        
        # Legacy rate properties
        assert profile.rate_min == 90
        assert profile.rate_max == 120
        assert profile.rate_preferred == 105
        
        # Legacy CV properties
        assert profile.cv_de == "cv_de.pdf"
        assert profile.cv_en == "cv_en.pdf"
        
        # Legacy keyword properties
        assert "python" in profile.must_have


class TestProfileLoader:
    """Test YAML loading functions."""
    
    def test_load_profile_wolfram(self):
        """Should load Wolfram profile."""
        from modules.profiles import load_profile
        
        wolfram = load_profile("wolfram")
        
        assert wolfram.name == "Wolfram Laube"
        assert wolfram.email == "wolfram.laube@blauweiss-edv.at"
        assert wolfram.phone == "+43 664 4011521"
        assert wolfram.rate.preferred == 105
        assert "kubernetes" in wolfram.keywords.must_have
        assert "python" in wolfram.keywords.must_have
    
    def test_load_profile_ian(self):
        """Should load Ian profile."""
        from modules.profiles import load_profile
        
        ian = load_profile("ian")
        
        assert ian.name == "Ian Matejka"
        assert "llm" in ian.keywords.must_have
        assert "pytorch" in ian.keywords.must_have
    
    def test_load_profile_michael(self):
        """Should load Michael profile."""
        from modules.profiles import load_profile
        
        michael = load_profile("michael")
        
        assert michael.name == "Michael Matejka"
        assert "project manager" in michael.keywords.must_have
    
    def test_load_profile_not_found(self):
        """Should raise KeyError for unknown profile."""
        from modules.profiles import load_profile
        
        with pytest.raises(KeyError):
            load_profile("unknown_profile")
    
    def test_load_all_profiles(self):
        """Should load all profiles as dict."""
        from modules.profiles import load_all_profiles
        
        profiles = load_all_profiles()
        
        assert "wolfram" in profiles
        assert "ian" in profiles
        assert "michael" in profiles
        assert len(profiles) == 3
    
    def test_get_team_config(self):
        """Should load team with resolved members."""
        from modules.profiles import get_team_config
        
        team = get_team_config("wolfram_ian")
        
        assert team.name == "Wolfram Laube & Ian Matejka"
        assert team.primary_contact == "wolfram"
        assert len(team.member_profiles) == 2
        assert team.member_profiles[0].name == "Wolfram Laube"
    
    def test_list_available(self):
        """Should list all profiles and teams."""
        from modules.profiles import list_available
        
        available = list_available()
        
        assert "profiles" in available
        assert "teams" in available
        assert "wolfram" in available["profiles"]
        assert "wolfram_ian" in available["teams"]


class TestProfileMatching:
    """Test keyword matching logic."""
    
    def test_match_profile_basic(self):
        """Should match keywords in text."""
        from modules.profiles import load_profile, match_profile
        
        wolfram = load_profile("wolfram")
        
        text = "Senior DevOps Engineer mit Kubernetes und Python Erfahrung"
        result = match_profile(wolfram, text)
        
        assert result["percentage"] > 0
        assert "kubernetes" in result["matches"]["must_have"]
        assert "python" in result["matches"]["must_have"]
        assert result["excluded_by"] is None
    
    def test_match_profile_exclusion(self):
        """Should exclude on matching exclude keywords."""
        from modules.profiles import load_profile, match_profile
        
        wolfram = load_profile("wolfram")
        
        text = "Junior Python Developer - Praktikum"
        result = match_profile(wolfram, text)
        
        assert result["percentage"] == 0
        assert result["excluded_by"] in ["junior", "praktikum"]
    
    def test_match_profile_high_score(self):
        """Should give high score for many matches."""
        from modules.profiles import load_profile, match_profile
        
        wolfram = load_profile("wolfram")
        
        text = """
        Senior Solution Architect für Cloud Migration.
        Kubernetes, Docker, AWS, Terraform erforderlich.
        Python und Java Kenntnisse. CI/CD mit GitLab.
        Erfahrung mit Kafka und Prometheus von Vorteil.
        """
        result = match_profile(wolfram, text)
        
        assert result["percentage"] >= 70
        assert len(result["matches"]["must_have"]) >= 5
    
    def test_get_best_matches(self):
        """Should return sorted list of matches."""
        from modules.profiles import get_best_matches
        
        text = "AI/ML Engineer für LLM Development mit Python und PyTorch"
        matches = get_best_matches(text, min_percentage=20)
        
        assert len(matches) > 0
        # Ian should match best for AI/ML
        assert matches[0]["profile"] in ["ian", "wolfram"]
    
    def test_match_team(self):
        """Should match team keywords."""
        from modules.profiles import get_team_config, match_team
        
        team = get_team_config("wolfram_ian")
        
        text = "AI Platform mit MLOps, Kubernetes und Python"
        result = match_team(team, text)
        
        assert result["percentage"] > 0
        assert len(result["matches"]) > 0


class TestLegacyCompatibility:
    """Test backwards compatibility with old imports."""
    
    def test_legacy_constants(self):
        """WOLFRAM, IAN, MICHAEL should exist."""
        from modules.profiles import WOLFRAM, IAN, MICHAEL
        
        assert WOLFRAM.name == "Wolfram Laube"
        assert IAN.name == "Ian Matejka"
        assert MICHAEL.name == "Michael Matejka"
    
    def test_legacy_match_score(self):
        """WOLFRAM.match_score() should work."""
        from modules.profiles import WOLFRAM
        
        result = WOLFRAM.match_score("Python Kubernetes DevOps")
        
        assert "percentage" in result
        assert "matches" in result
        assert result["percentage"] > 0
    
    def test_legacy_profiles_dict(self):
        """PROFILES dict should work."""
        from modules.profiles import PROFILES
        
        assert "wolfram" in PROFILES
        assert "ian" in PROFILES
        assert "michael" in PROFILES
        
        assert PROFILES["wolfram"].name == "Wolfram Laube"
    
    def test_legacy_team_combos(self):
        """TEAM_COMBOS dict should work."""
        from modules.profiles import TEAM_COMBOS
        
        assert "wolfram_ian" in TEAM_COMBOS
        assert "all_three" in TEAM_COMBOS
        
        combo = TEAM_COMBOS["wolfram_ian"]
        assert "name" in combo
        assert "keywords" in combo
    
    def test_legacy_dict_api(self):
        """load_profile_dict should return dict."""
        from modules.profiles import load_profile_dict
        
        profile = load_profile_dict("wolfram")
        
        assert isinstance(profile, dict)
        assert profile["name"] == "Wolfram Laube"
        assert "key" in profile
        assert isinstance(profile["attachments"], list)  # Flattened

