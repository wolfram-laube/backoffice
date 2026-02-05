"""
Tests for Job Requirement Parser (#23)

pytest tests/test_parser.py -v
"""

import pytest
from nsai.parser import JobRequirementParser, JobRequirements


class TestJobRequirements:
    """Tests for JobRequirements dataclass."""
    
    def test_creation(self):
        reqs = JobRequirements(
            job_name="test-job",
            required_capabilities=["docker"],
            preferred_capabilities=["linux"]
        )
        assert reqs.job_name == "test-job"
        assert "docker" in reqs.required_capabilities
    
    def test_is_feasible_for(self):
        reqs = JobRequirements(
            required_capabilities=["docker", "linux"],
            excluded_capabilities=["windows"]
        )
        
        # Feasible: has all required, no excluded
        assert reqs.is_feasible_for({"docker", "linux", "gcp"}) is True
        
        # Not feasible: missing required
        assert reqs.is_feasible_for({"docker"}) is False
        
        # Not feasible: has excluded
        assert reqs.is_feasible_for({"docker", "linux", "windows"}) is False
    
    def test_preference_score(self):
        reqs = JobRequirements(preferred_capabilities=["gpu", "arm64"])
        
        # Full match
        assert reqs.preference_score({"gpu", "arm64"}) == 1.0
        
        # Half match
        assert reqs.preference_score({"gpu"}) == 0.5
        
        # No match
        assert reqs.preference_score({"docker"}) == 0.0
    
    def test_preference_score_empty(self):
        reqs = JobRequirements()
        # No preferences means everything scores 1.0
        assert reqs.preference_score({"anything"}) == 1.0


class TestJobRequirementParser:
    """Tests for JobRequirementParser class."""
    
    @pytest.fixture
    def parser(self):
        return JobRequirementParser()
    
    def test_parse_simple_tags(self, parser):
        job = {"tags": ["docker-any"]}
        reqs = parser.parse(job, "test")
        
        assert "docker" in reqs.required_capabilities
        assert reqs.tags == ["docker-any"]
    
    def test_parse_multiple_tags(self, parser):
        job = {"tags": ["docker-any", "gcp", "nordic"]}
        reqs = parser.parse(job, "test")
        
        assert "docker" in reqs.required_capabilities
        assert "gcp" in reqs.required_capabilities
        assert "nordic" in reqs.required_capabilities
    
    def test_parse_unknown_tag(self, parser):
        job = {"tags": ["my-special-tag"]}
        reqs = parser.parse(job, "test")
        
        # Unknown tags become capabilities directly
        assert "my-special-tag" in reqs.required_capabilities
    
    def test_parse_image_implies_docker(self, parser):
        job = {"image": "python:3.11"}
        reqs = parser.parse(job, "test")
        
        assert "docker" in reqs.required_capabilities
    
    def test_parse_nvidia_image(self, parser):
        job = {"image": "nvidia/cuda:11.8-base"}
        reqs = parser.parse(job, "test")
        
        assert "docker" in reqs.required_capabilities
        assert "gpu" in reqs.preferred_capabilities
    
    def test_parse_services(self, parser):
        job = {
            "image": "python:3.11",
            "services": ["postgres:15", "redis:7"]
        }
        reqs = parser.parse(job, "test")
        
        assert "linux" in reqs.preferred_capabilities
    
    def test_parse_timeout_simple(self, parser):
        job = {"timeout": "30m"}
        reqs = parser.parse(job, "test")
        
        assert reqs.timeout_seconds == 30 * 60
    
    def test_parse_timeout_complex(self, parser):
        job = {"timeout": "1h 30m"}
        reqs = parser.parse(job, "test")
        
        assert reqs.timeout_seconds == 90 * 60
    
    def test_parse_yaml(self, parser):
        yaml_content = """
default:
  tags:
    - docker-any

stages:
  - test
  - build

test-unit:
  stage: test
  image: python:3.11
  script:
    - pytest

build-image:
  stage: build
  tags:
    - docker-any
    - gcp
  script:
    - docker build .
"""
        jobs = parser.parse_yaml(yaml_content)
        
        assert "test-unit" in jobs
        assert "build-image" in jobs
        
        # test-unit should have default tags
        assert "docker" in jobs["test-unit"].required_capabilities
        
        # build-image has explicit tags
        assert "gcp" in jobs["build-image"].required_capabilities
    
    def test_custom_tag_mapping(self):
        parser = JobRequirementParser(tag_mappings={
            "my-team": ["docker", "linux", "gcp"]
        })
        
        job = {"tags": ["my-team"]}
        reqs = parser.parse(job, "test")
        
        assert "docker" in reqs.required_capabilities
        assert "linux" in reqs.required_capabilities
        assert "gcp" in reqs.required_capabilities
    
    def test_deduplicate_capabilities(self, parser):
        # Tags that map to overlapping capabilities
        job = {"tags": ["docker-any", "docker"]}
        reqs = parser.parse(job, "test")
        
        # Should not have duplicates
        assert reqs.required_capabilities.count("docker") == 1
