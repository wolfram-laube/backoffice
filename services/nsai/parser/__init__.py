"""
Job Requirement Parser Module (#23)

Extracts runner requirements from .gitlab-ci.yml job definitions.
Provides the input for constraint-based runner filtering.
"""

from .job_parser import JobRequirementParser, JobRequirements

__all__ = ["JobRequirementParser", "JobRequirements"]
