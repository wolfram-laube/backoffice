"""
NSAI - Neurosymbolic AI Runner Selection

A two-layer architecture combining symbolic reasoning (Knowledge Graph,
Constraint Satisfaction) with subsymbolic learning (Multi-Armed Bandits)
for intelligent CI/CD runner selection.

Architecture:
    Symbolic Layer (this package):
        - ontology: Runner Capability Ontology (OWL/RDF)
        - parser: Job Requirement Parser (.gitlab-ci.yml)
        - csp: Constraint Satisfaction Problem solver
    
    Subsymbolic Layer (runner_bandit service):
        - UCB1, Thompson Sampling, ε-Greedy bandits
    
    Integration (interface module):
        - Neural-Symbolic bidirectional communication

Related:
    - ADR: AI-001 Neurosymbolic Runner Selection Architecture
    - Epic: #27 [EPIC] Neurosymbolic AI Runner Selection
    - Paper: #26 JKU Bachelor Paper Draft
"""

__version__ = "0.1.0"
__author__ = "Wolfram Laube"

from .ontology import RunnerOntology
from .parser import JobRequirementParser
from .csp import ConstraintSolver

__all__ = ["RunnerOntology", "JobRequirementParser", "ConstraintSolver"]
