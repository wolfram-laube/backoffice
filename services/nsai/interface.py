"""
Neurosymbolic Interface - Connects Symbolic and Subsymbolic Layers

This module implements the NeurosymbolicBandit class that bridges:
- Symbolic Layer: CSP Solver (constraint satisfaction, hard rules)
- Subsymbolic Layer: MAB (adaptive learning, exploration/exploitation)

Flow:
    Job Requirements → CSP (Feasible Set) → MAB (Optimal Selection) → Runner

Issue: #25
Epic: #27 Neurosymbolic AI Runner Selection
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum, auto
import time

from .csp import ConstraintSolver, SelectionResult, SolverStatus
from .ontology import RunnerOntology, create_blauweiss_ontology
from .parser import JobRequirementParser, JobRequirements


@dataclass
class Explanation:
    """
    Human-readable explanation of the runner selection decision.
    
    Provides transparency into both symbolic and subsymbolic reasoning.
    """
    symbolic_reasoning: str       # Why certain runners were filtered
    statistical_reasoning: str    # Why the selected runner was chosen
    feasible_runners: List[str]   # Runners that passed symbolic filtering
    selected_runner: str          # Final selection
    confidence: float             # Confidence in selection (0-1)
    solve_time_ms: float         # Total decision time
    
    def __str__(self) -> str:
        lines = [
            "=== Runner Selection Explanation ===",
            "",
            "📐 Symbolic Layer (CSP):",
            self.symbolic_reasoning,
            "",
            "🎰 Subsymbolic Layer (MAB):",
            self.statistical_reasoning,
            "",
            f"✅ Selected: {self.selected_runner}",
            f"📊 Confidence: {self.confidence:.1%}",
            f"⏱️ Decision time: {self.solve_time_ms:.2f}ms"
        ]
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        return {
            "symbolic_reasoning": self.symbolic_reasoning,
            "statistical_reasoning": self.statistical_reasoning,
            "feasible_runners": self.feasible_runners,
            "selected_runner": self.selected_runner,
            "confidence": self.confidence,
            "solve_time_ms": self.solve_time_ms
        }


class NeurosymbolicBandit:
    """
    Neurosymbolic Runner Selection combining CSP and MAB.
    
    Two-layer architecture:
    1. Symbolic (CSP): Filters runners by hard constraints
       - Required capabilities (must have)
       - Excluded capabilities (must not have)
       - Online status, cost limits
       → Produces FEASIBLE SET
    
    2. Subsymbolic (MAB): Selects optimal from feasible set
       - UCB1 exploration/exploitation
       - Learns from historical performance
       → Produces SELECTION + EXPLANATION
    
    Example:
        >>> nsai = NeurosymbolicBandit.create_default()
        >>> runner, explanation = nsai.select_runner({
        ...     "tags": ["docker-any"],
        ...     "image": "python:3.11"
        ... })
        >>> print(f"Selected: {runner}")
        >>> print(explanation)
    
    Attributes:
        symbolic: CSP constraint solver
        bandit_stats: Per-runner performance statistics
        exploration_constant: UCB1 exploration parameter
    """
    
    def __init__(
        self,
        solver: ConstraintSolver,
        exploration_constant: float = 2.0
    ):
        """
        Initialize the neurosymbolic bandit.
        
        Args:
            solver: CSP constraint solver with ontology
            exploration_constant: UCB1 c parameter (higher = more exploration)
        """
        self.symbolic = solver
        self.c = exploration_constant
        
        # Initialize bandit stats for all known runners
        self._stats: Dict[str, dict] = {}
        for name in solver.ontology.runners:
            self._stats[name] = {
                "pulls": 0,
                "total_reward": 0.0,
                "successes": 0,
                "failures": 0,
                "total_duration": 0.0
            }
        
        self._total_pulls = 0
    
    @classmethod
    def create_default(cls) -> "NeurosymbolicBandit":
        """Factory method with production defaults."""
        solver = ConstraintSolver(
            ontology=create_blauweiss_ontology(),
            parser=JobRequirementParser()
        )
        return cls(solver)
    
    def select_runner(
        self,
        job_definition: Dict[str, Any],
        job_name: str = ""
    ) -> Tuple[Optional[str], Explanation]:
        """
        Select optimal runner using neurosymbolic reasoning.
        
        Args:
            job_definition: Job definition from .gitlab-ci.yml
            job_name: Name of the job
        
        Returns:
            Tuple of (selected_runner, explanation)
            If no feasible runner exists, selected_runner is None
        """
        start_time = time.perf_counter()
        
        # ===== SYMBOLIC LAYER =====
        csp_result = self.symbolic.solve(job_definition, job_name)
        
        if not csp_result.is_feasible:
            return None, Explanation(
                symbolic_reasoning=csp_result.explanation,
                statistical_reasoning="N/A - No feasible runners",
                feasible_runners=[],
                selected_runner="",
                confidence=0.0,
                solve_time_ms=(time.perf_counter() - start_time) * 1000
            )
        
        feasible = csp_result.feasible_runners
        
        # ===== SUBSYMBOLIC LAYER =====
        # UCB1 selection from feasible set only
        selected, confidence, stat_reasoning = self._ucb1_select(feasible)
        
        solve_time = (time.perf_counter() - start_time) * 1000
        
        explanation = Explanation(
            symbolic_reasoning=csp_result.explanation,
            statistical_reasoning=stat_reasoning,
            feasible_runners=feasible,
            selected_runner=selected,
            confidence=confidence,
            solve_time_ms=solve_time
        )
        
        return selected, explanation
    
    def _ucb1_select(
        self,
        candidates: List[str]
    ) -> Tuple[str, float, str]:
        """
        UCB1 selection with dynamic action space.
        
        Key insight: By limiting to feasible candidates, we get
        FASTER CONVERGENCE than vanilla bandit on full runner set.
        
        Args:
            candidates: Feasible runners from CSP
        
        Returns:
            Tuple of (selected, confidence, reasoning)
        """
        import math
        
        reasoning_lines = [f"Evaluating {len(candidates)} feasible runners:"]
        
        # Exploration phase: try each candidate at least once
        for runner in candidates:
            if self._stats[runner]["pulls"] == 0:
                reasoning_lines.append(f"  → {runner}: Unexplored, selecting for exploration")
                return runner, 0.5, "\n".join(reasoning_lines)
        
        # UCB1 calculation
        ucb_values = {}
        total_pulls_feasible = sum(self._stats[r]["pulls"] for r in candidates)
        
        for runner in candidates:
            stats = self._stats[runner]
            mean_reward = stats["total_reward"] / stats["pulls"]
            exploration_bonus = self.c * math.sqrt(
                math.log(total_pulls_feasible + 1) / stats["pulls"]
            )
            ucb = mean_reward + exploration_bonus
            ucb_values[runner] = ucb
            
            reasoning_lines.append(
                f"  → {runner}: μ={mean_reward:.3f}, "
                f"explore={exploration_bonus:.3f}, UCB={ucb:.3f}"
            )
        
        # Select highest UCB
        selected = max(ucb_values, key=ucb_values.get)
        
        # Confidence: how much better is selected vs second best?
        sorted_ucb = sorted(ucb_values.values(), reverse=True)
        if len(sorted_ucb) > 1 and sorted_ucb[0] > 0:
            confidence = min(1.0, sorted_ucb[0] / (sorted_ucb[1] + 0.001))
        else:
            confidence = 1.0
        
        reasoning_lines.append(f"  ✓ Selected {selected} (UCB={ucb_values[selected]:.3f})")
        
        return selected, confidence, "\n".join(reasoning_lines)
    
    def update(
        self,
        runner: str,
        success: bool,
        duration_seconds: float,
        cost_per_minute: float = 0.0
    ):
        """
        Update bandit statistics after observing job outcome.
        
        Args:
            runner: Runner that executed the job
            success: Whether job succeeded
            duration_seconds: Job duration
            cost_per_minute: Runner cost
        """
        if runner not in self._stats:
            raise ValueError(f"Unknown runner: {runner}")
        
        # Calculate reward (higher is better)
        if success:
            duration_minutes = duration_seconds / 60.0
            cost_penalty = cost_per_minute * duration_minutes
            reward = 1.0 / (duration_minutes + cost_penalty + 0.1)
        else:
            reward = 0.0
        
        stats = self._stats[runner]
        stats["pulls"] += 1
        stats["total_reward"] += reward
        stats["total_duration"] += duration_seconds
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        
        self._total_pulls += 1
    
    def get_stats(self) -> Dict[str, dict]:
        """Return current statistics for all runners."""
        return {
            runner: {
                "pulls": s["pulls"],
                "mean_reward": round(s["total_reward"] / s["pulls"], 4) if s["pulls"] > 0 else 0.0,
                "success_rate": round(s["successes"] / (s["successes"] + s["failures"]), 4) 
                    if (s["successes"] + s["failures"]) > 0 else 0.5,
                "avg_duration": round(s["total_duration"] / s["pulls"], 2) if s["pulls"] > 0 else 0.0
            }
            for runner, s in self._stats.items()
        }
    
    def sync_from_mab_service(self, stats: Dict[str, dict]):
        """
        Sync statistics from external MAB service.
        
        Handles name mapping: MAB service uses its own runner names,
        which may differ from ontology names. Uses ontology mab_tag mapping.
        
        Args:
            stats: Stats dict from MAB service /stats endpoint
                   Keys are MAB runner names (e.g. "gitlab-runner-nordic")
        """
        ontology = self.symbolic.ontology
        
        for mab_runner_name, data in stats.items():
            # Try direct match first, then MAB tag resolution
            target = None
            if mab_runner_name in self._stats:
                target = mab_runner_name
            else:
                # Try to resolve via ontology MAB tag mapping
                resolved = ontology.runner_name_for_mab_tag(mab_runner_name)
                if resolved and resolved in self._stats:
                    target = resolved
            
            if target is None:
                continue
            
            # Approximate reconstruction from summary stats
            pulls = data.get("pulls", 0)
            self._stats[target]["pulls"] = pulls
            self._stats[target]["successes"] = int(
                pulls * data.get("success_rate", 0.5)
            )
            self._stats[target]["failures"] = (
                pulls - self._stats[target]["successes"]
            )
            self._stats[target]["total_duration"] = (
                pulls * data.get("avg_duration", 0)
            )
            self._stats[target]["total_reward"] = (
                data.get("mean_reward", 0) * max(pulls, 1)
            )
        
        self._total_pulls = sum(s["pulls"] for s in self._stats.values())
    
    @classmethod
    def from_live_service(cls, service_url: str = "https://runner-bandit-m5cziijwqa-lz.a.run.app") -> "NeurosymbolicBandit":
        """
        Factory: create NSAI instance warm-started from live MAB service.
        
        Args:
            service_url: Base URL of the MAB Cloud Run service
            
        Returns:
            NeurosymbolicBandit with stats synced from live service
        """
        import urllib.request
        import json as _json
        
        nsai = cls.create_default()
        
        try:
            req = urllib.request.Request(f"{service_url}/stats")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read())
            
            runners_stats = data.get("runners", {})
            nsai.sync_from_mab_service(runners_stats)
        except Exception:
            pass  # Fall back to cold start
        
        return nsai


# Convenience alias
NSAI = NeurosymbolicBandit
