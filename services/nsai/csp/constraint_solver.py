"""
Constraint Satisfaction Problem Solver

Integrates the ontology and parser to solve the runner selection CSP.
Produces a feasible set of runners for the MAB layer to choose from.

Classes:
    SelectionResult: Result of constraint satisfaction
    ConstraintSolver: Main CSP solver

Example:
    >>> from nsai.ontology import create_blauweiss_ontology
    >>> from nsai.parser import JobRequirementParser
    >>> from nsai.csp import ConstraintSolver
    >>> 
    >>> solver = ConstraintSolver(
    ...     ontology=create_blauweiss_ontology(),
    ...     parser=JobRequirementParser()
    ... )
    >>> result = solver.solve({"tags": ["docker-any"]})
    >>> print(result.feasible_runners)  # ["gitlab-runner-nordic"]
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum, auto
import time

# Import sibling modules (will work when package is installed)
try:
    from ..ontology import RunnerOntology
    from ..parser import JobRequirementParser, JobRequirements
except ImportError:
    # For standalone testing
    from ontology.runner_ontology import RunnerOntology
    from parser.job_parser import JobRequirementParser, JobRequirements


class SolverStatus(Enum):
    """Status of CSP solving."""
    FEASIBLE = auto()      # Found at least one valid runner
    INFEASIBLE = auto()    # No runner satisfies constraints
    TIMEOUT = auto()       # Solving took too long
    ERROR = auto()         # Error during solving


@dataclass
class SelectionResult:
    """
    Result of the constraint satisfaction process.
    
    Attributes:
        status: Solving outcome
        feasible_runners: List of runner names that satisfy constraints
        ranked_runners: Runners sorted by preference score
        requirements: The parsed job requirements
        pruned_runners: Runners eliminated and why
        solve_time_ms: Time taken to solve
        explanation: Human-readable explanation
    """
    status: SolverStatus
    feasible_runners: List[str] = field(default_factory=list)
    ranked_runners: List[Tuple[str, float]] = field(default_factory=list)
    requirements: Optional[JobRequirements] = None
    pruned_runners: Dict[str, str] = field(default_factory=dict)
    solve_time_ms: float = 0.0
    explanation: str = ""
    
    @property
    def is_feasible(self) -> bool:
        return self.status == SolverStatus.FEASIBLE
    
    @property
    def best_runner(self) -> Optional[str]:
        """Get highest-ranked runner, if any."""
        if self.ranked_runners:
            return self.ranked_runners[0][0]
        return None
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "status": self.status.name,
            "feasible_runners": self.feasible_runners,
            "ranked_runners": self.ranked_runners,
            "requirements": self.requirements.to_dict() if self.requirements else None,
            "pruned_runners": self.pruned_runners,
            "solve_time_ms": self.solve_time_ms,
            "explanation": self.explanation
        }


class ConstraintSolver:
    """
    Constraint Satisfaction Problem solver for runner selection.
    
    Combines the Runner Ontology (knowledge) with Job Requirements (query)
    to find feasible runners. This is the symbolic layer that filters
    candidates before passing to the MAB (subsymbolic) layer.
    
    Architecture:
        Job Definition → Parser → Requirements
                                      ↓
        Runner Ontology → CSP Solver → Feasible Set → MAB
    
    Attributes:
        ontology: Runner capability knowledge base
        parser: Job requirement extractor
    """
    
    def __init__(self, ontology: RunnerOntology, 
                 parser: JobRequirementParser = None):
        """
        Initialize solver with ontology and parser.
        
        Args:
            ontology: Runner capability ontology
            parser: Job requirement parser (created if not provided)
        """
        self.ontology = ontology
        self.parser = parser or JobRequirementParser()
    
    def solve(self, job_definition: Dict[str, Any],
              job_name: str = "",
              include_offline: bool = False) -> SelectionResult:
        """
        Solve the runner selection CSP for a job.
        
        Args:
            job_definition: Job definition from .gitlab-ci.yml
            job_name: Name of the job
            include_offline: Whether to include offline runners
            
        Returns:
            SelectionResult with feasible runners
        """
        start_time = time.perf_counter()
        
        # Parse requirements
        requirements = self.parser.parse(job_definition, job_name)
        
        # Find feasible runners
        feasible = []
        pruned = {}
        
        for name, runner in self.ontology.runners.items():
            # Check online status
            if not runner.online and not include_offline:
                pruned[name] = "offline"
                continue
            
            # Check required capabilities
            runner_caps = {c.name for c in runner.capabilities}
            missing = [c for c in requirements.required_capabilities 
                      if c not in runner_caps]
            if missing:
                pruned[name] = f"missing: {', '.join(missing)}"
                continue
            
            # Check excluded capabilities
            forbidden = [c for c in requirements.excluded_capabilities 
                        if c in runner_caps]
            if forbidden:
                pruned[name] = f"has excluded: {', '.join(forbidden)}"
                continue
            
            feasible.append(name)
        
        # Rank by preference score
        ranked = []
        for name in feasible:
            runner = self.ontology.runners[name]
            runner_caps = {c.name for c in runner.capabilities}
            score = requirements.preference_score(runner_caps)
            ranked.append((name, score))
        
        # Sort by score descending, then by cost ascending
        ranked.sort(key=lambda x: (-x[1], 
                                   self.ontology.runners[x[0]].cost_per_minute))
        
        solve_time = (time.perf_counter() - start_time) * 1000
        
        # Determine status
        if feasible:
            status = SolverStatus.FEASIBLE
            explanation = self._generate_explanation(requirements, ranked, pruned)
        else:
            status = SolverStatus.INFEASIBLE
            explanation = self._generate_infeasible_explanation(requirements, pruned)
        
        return SelectionResult(
            status=status,
            feasible_runners=feasible,
            ranked_runners=ranked,
            requirements=requirements,
            pruned_runners=pruned,
            solve_time_ms=solve_time,
            explanation=explanation
        )
    
    def solve_batch(self, jobs: Dict[str, Dict[str, Any]]) -> Dict[str, SelectionResult]:
        """
        Solve for multiple jobs at once.
        
        Args:
            jobs: Dictionary of job_name -> job_definition
            
        Returns:
            Dictionary of job_name -> SelectionResult
        """
        return {
            name: self.solve(job_def, job_name=name)
            for name, job_def in jobs.items()
        }
    
    def _generate_explanation(self, requirements: JobRequirements,
                              ranked: List[Tuple[str, float]],
                              pruned: Dict[str, str]) -> str:
        """Generate human-readable explanation of the selection."""
        lines = []
        
        lines.append(f"Job requires: {', '.join(requirements.required_capabilities) or 'none'}")
        
        if requirements.preferred_capabilities:
            lines.append(f"Prefers: {', '.join(requirements.preferred_capabilities)}")
        
        lines.append(f"Feasible runners: {len(ranked)}")
        
        for name, score in ranked[:3]:  # Top 3
            runner = self.ontology.runners[name]
            lines.append(f"  • {name} (score: {score:.2f}, cost: €{runner.cost_per_minute:.3f}/min)")
        
        if pruned:
            lines.append(f"Pruned: {len(pruned)} runners")
        
        return "\n".join(lines)
    
    def _generate_infeasible_explanation(self, requirements: JobRequirements,
                                         pruned: Dict[str, str]) -> str:
        """Explain why no runner was feasible."""
        lines = [
            "❌ No feasible runner found!",
            f"Required capabilities: {', '.join(requirements.required_capabilities)}",
            "Reasons:"
        ]
        
        for name, reason in pruned.items():
            lines.append(f"  • {name}: {reason}")
        
        lines.append("\nSuggestions:")
        lines.append("  - Check if required runners are online")
        lines.append("  - Verify tag mappings in parser configuration")
        lines.append("  - Consider adding capabilities to existing runners")
        
        return "\n".join(lines)
    
    def get_runner_recommendation(self, job_definition: Dict[str, Any],
                                   job_name: str = "") -> Optional[str]:
        """
        Convenience method to get single best runner.
        
        This is what the MAB layer would call if it wants a 
        symbolically-informed baseline recommendation.
        
        Args:
            job_definition: Job definition
            job_name: Job name
            
        Returns:
            Best runner name or None if infeasible
        """
        result = self.solve(job_definition, job_name)
        return result.best_runner


# Factory function for production use
def create_solver() -> ConstraintSolver:
    """Create a solver with the blauweiss production ontology."""
    from ..ontology.runner_ontology import create_blauweiss_ontology
    return ConstraintSolver(
        ontology=create_blauweiss_ontology(),
        parser=JobRequirementParser()
    )
