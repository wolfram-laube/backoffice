"""
NSAI - Neurosymbolic AI Runner Selection

A two-layer architecture combining symbolic reasoning (CSP)
with adaptive learning (MAB) for intelligent CI/CD runner selection.

Quick Start:
    >>> from nsai import NeurosymbolicBandit
    >>> nsai = NeurosymbolicBandit.create_default()
    >>> runner, explanation = nsai.select_runner({"tags": ["docker-any"]})

Modules:
    - ontology: Runner capability knowledge base
    - parser: Job requirement extraction
    - csp: Constraint satisfaction solver
    - interface: Neurosymbolic integration (CSP + MAB)

See Also:
    - README.md for architecture overview
    - Epic #27 for project tracking
"""

from .ontology import RunnerOntology, create_blauweiss_ontology
from .parser import JobRequirementParser, JobRequirements
from .csp import ConstraintSolver, SelectionResult, SolverStatus
from .interface import NeurosymbolicBandit, Explanation, NSAI

__all__ = [
    # Core classes
    "NeurosymbolicBandit",
    "NSAI",
    "Explanation",
    # Symbolic layer
    "ConstraintSolver",
    "SelectionResult", 
    "SolverStatus",
    "RunnerOntology",
    "create_blauweiss_ontology",
    # Parser
    "JobRequirementParser",
    "JobRequirements",
]

__version__ = "0.3.0"
