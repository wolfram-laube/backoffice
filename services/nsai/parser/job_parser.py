"""
Job Requirement Parser

Extracts runner requirements from GitLab CI job definitions.
Parses tags, resource requirements, and implicit constraints.

Classes:
    JobRequirements: Structured representation of job requirements
    JobRequirementParser: Parser for .gitlab-ci.yml job definitions

Example:
    >>> parser = JobRequirementParser()
    >>> job_def = {"tags": ["docker-any"], "image": "python:3.11"}
    >>> reqs = parser.parse(job_def)
    >>> print(reqs.required_capabilities)  # ["docker"]
    >>> print(reqs.preferred_capabilities)  # ["linux"]
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
import re
import yaml


@dataclass
class JobRequirements:
    """
    Structured representation of job requirements.
    
    Attributes:
        job_name: Name of the CI job
        required_capabilities: Must-have capabilities (hard constraints)
        preferred_capabilities: Nice-to-have capabilities (soft constraints)
        excluded_capabilities: Must-not-have capabilities
        resource_hints: Resource requirements (memory, CPU, GPU)
        timeout_seconds: Maximum job duration
        tags: Original GitLab tags
    """
    job_name: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    preferred_capabilities: List[str] = field(default_factory=list)
    excluded_capabilities: List[str] = field(default_factory=list)
    resource_hints: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    
    def is_feasible_for(self, runner_capabilities: Set[str]) -> bool:
        """Check if a runner with given capabilities can run this job."""
        # All required capabilities must be present
        if not all(cap in runner_capabilities for cap in self.required_capabilities):
            return False
        # No excluded capabilities may be present
        if any(cap in runner_capabilities for cap in self.excluded_capabilities):
            return False
        return True
    
    def preference_score(self, runner_capabilities: Set[str]) -> float:
        """
        Calculate preference score for ranking feasible runners.
        
        Returns:
            Score between 0.0 and 1.0 based on preferred capabilities match
        """
        if not self.preferred_capabilities:
            return 1.0
        matched = sum(1 for cap in self.preferred_capabilities if cap in runner_capabilities)
        return matched / len(self.preferred_capabilities)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "job_name": self.job_name,
            "required": self.required_capabilities,
            "preferred": self.preferred_capabilities,
            "excluded": self.excluded_capabilities,
            "resource_hints": self.resource_hints,
            "timeout": self.timeout_seconds,
            "tags": self.tags
        }


class JobRequirementParser:
    """
    Parser for GitLab CI job definitions.
    
    Extracts explicit tags and infers implicit requirements from
    job configuration (images, services, scripts, etc.).
    
    Attributes:
        tag_mappings: Maps GitLab tags to capability names
        image_patterns: Regex patterns to infer capabilities from images
    """
    
    # Map common tags to capabilities
    DEFAULT_TAG_MAPPINGS = {
        "docker-any": ["docker"],
        "docker": ["docker"],
        "shell": ["shell"],
        "kubernetes": ["kubernetes"],
        "k8s": ["kubernetes"],
        "gcp": ["gcp"],
        "aws": ["aws"],
        "azure": ["azure"],
        "gpu": ["gpu"],
        "nordic": ["nordic", "gcp"],
        "macos": ["macos", "shell"],
        "windows": ["windows"],
        "linux": ["linux"],
        "arm64": ["arm64"],
        "local": ["local"],
    }
    
    # Infer capabilities from Docker image names
    IMAGE_CAPABILITY_PATTERNS = [
        (r"nvidia|cuda", ["gpu"]),
        (r"arm64|aarch64", ["arm64"]),
        (r"windows", ["windows"]),
        (r"alpine|ubuntu|debian|centos", ["linux"]),
    ]
    
    # Services that imply capabilities
    SERVICE_CAPABILITIES = {
        "docker:dind": ["docker"],
        "postgres": ["linux"],
        "mysql": ["linux"],
        "redis": ["linux"],
        "mongo": ["linux"],
    }
    
    def __init__(self, tag_mappings: Dict[str, List[str]] = None):
        """
        Initialize parser with optional custom tag mappings.
        
        Args:
            tag_mappings: Custom tag-to-capability mappings
        """
        self.tag_mappings = {**self.DEFAULT_TAG_MAPPINGS}
        if tag_mappings:
            self.tag_mappings.update(tag_mappings)
    
    def parse(self, job_definition: Dict[str, Any], 
              job_name: str = "") -> JobRequirements:
        """
        Parse a job definition and extract requirements.
        
        Args:
            job_definition: Dictionary from parsed .gitlab-ci.yml
            job_name: Name of the job
            
        Returns:
            JobRequirements with extracted constraints
        """
        reqs = JobRequirements(job_name=job_name)
        
        # Extract explicit tags
        tags = job_definition.get("tags", [])
        reqs.tags = tags.copy() if isinstance(tags, list) else [tags]
        
        # Map tags to capabilities
        for tag in reqs.tags:
            tag_lower = tag.lower()
            if tag_lower in self.tag_mappings:
                reqs.required_capabilities.extend(self.tag_mappings[tag_lower])
            else:
                # Unknown tag becomes a required capability directly
                reqs.required_capabilities.append(tag_lower)
        
        # Infer from image
        image = job_definition.get("image", "")
        if image:
            reqs.required_capabilities.append("docker")  # Image implies Docker
            for pattern, caps in self.IMAGE_CAPABILITY_PATTERNS:
                if re.search(pattern, image, re.IGNORECASE):
                    reqs.preferred_capabilities.extend(caps)
        
        # Infer from services
        services = job_definition.get("services", [])
        for service in services:
            service_name = service if isinstance(service, str) else service.get("name", "")
            for svc_pattern, caps in self.SERVICE_CAPABILITIES.items():
                if svc_pattern in service_name:
                    reqs.preferred_capabilities.extend(caps)
        
        # Extract resource hints
        variables = job_definition.get("variables", {})
        if "CI_RUNNER_MEMORY" in variables:
            reqs.resource_hints["memory"] = variables["CI_RUNNER_MEMORY"]
        if "CI_RUNNER_CPU" in variables:
            reqs.resource_hints["cpu"] = variables["CI_RUNNER_CPU"]
        
        # Parse timeout
        timeout = job_definition.get("timeout", "")
        if timeout:
            reqs.timeout_seconds = self._parse_timeout(timeout)
        
        # Deduplicate while preserving order
        reqs.required_capabilities = list(dict.fromkeys(reqs.required_capabilities))
        reqs.preferred_capabilities = list(dict.fromkeys(reqs.preferred_capabilities))
        
        return reqs
    
    def parse_yaml(self, yaml_content: str) -> Dict[str, JobRequirements]:
        """
        Parse entire .gitlab-ci.yml and extract requirements for all jobs.
        
        Args:
            yaml_content: Raw YAML content
            
        Returns:
            Dictionary mapping job names to their requirements
        """
        config = yaml.safe_load(yaml_content)
        jobs = {}
        
        # Get default tags from default: section
        default_tags = []
        if "default" in config and "tags" in config["default"]:
            default_tags = config["default"]["tags"]
        
        for key, value in config.items():
            # Skip non-job keys
            if key.startswith(".") or key in ("default", "include", "variables", 
                                                "stages", "workflow", "image"):
                continue
            
            if isinstance(value, dict):
                # Apply default tags if job has no tags
                if "tags" not in value and default_tags:
                    value = {**value, "tags": default_tags}
                
                jobs[key] = self.parse(value, job_name=key)
        
        return jobs
    
    def _parse_timeout(self, timeout: str) -> int:
        """Parse GitLab timeout string to seconds."""
        if isinstance(timeout, int):
            return timeout
        
        # Handle formats like "1h 30m", "30 minutes", "3600"
        total_seconds = 0
        
        # Try direct integer
        try:
            return int(timeout)
        except ValueError:
            pass
        
        # Parse duration strings
        patterns = [
            (r"(\d+)\s*h", 3600),   # hours
            (r"(\d+)\s*m", 60),     # minutes  
            (r"(\d+)\s*s", 1),      # seconds
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, timeout, re.IGNORECASE)
            if match:
                total_seconds += int(match.group(1)) * multiplier
        
        return total_seconds if total_seconds > 0 else 3600  # Default 1h
    
    def add_tag_mapping(self, tag: str, capabilities: List[str]):
        """Add or update a tag-to-capabilities mapping."""
        self.tag_mappings[tag.lower()] = capabilities
