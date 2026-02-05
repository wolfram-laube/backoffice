"""
Constraint Satisfaction Module (#24)

Solves the runner selection problem as a CSP.
Integrates ontology and parser to find feasible runners.
"""

from .constraint_solver import ConstraintSolver, SelectionResult, SolverStatus

__all__ = ["ConstraintSolver", "SelectionResult", "SolverStatus"]
