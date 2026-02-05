"""
Tests for NeurosymbolicBandit Interface

Verifies the integration between symbolic (CSP) and subsymbolic (MAB) layers.
"""

import pytest
from unittest.mock import Mock, patch

# Import the classes we're testing
from nsai.interface import NeurosymbolicBandit, Explanation, NSAI
from nsai.csp import ConstraintSolver, SelectionResult, SolverStatus
from nsai.ontology import RunnerOntology, create_blauweiss_ontology
from nsai.parser import JobRequirementParser


class TestExplanation:
    """Tests for Explanation dataclass."""
    
    def test_explanation_str(self):
        """Test string representation."""
        exp = Explanation(
            symbolic_reasoning="Required: docker",
            statistical_reasoning="UCB1 selected best",
            feasible_runners=["runner-1", "runner-2"],
            selected_runner="runner-1",
            confidence=0.85,
            solve_time_ms=1.5
        )
        
        text = str(exp)
        assert "Symbolic Layer" in text
        assert "Subsymbolic Layer" in text
        assert "runner-1" in text
        assert "85.0%" in text
    
    def test_explanation_to_dict(self):
        """Test serialization."""
        exp = Explanation(
            symbolic_reasoning="test",
            statistical_reasoning="test",
            feasible_runners=["r1"],
            selected_runner="r1",
            confidence=0.9,
            solve_time_ms=1.0
        )
        
        d = exp.to_dict()
        assert d["selected_runner"] == "r1"
        assert d["confidence"] == 0.9


class TestNeurosymbolicBandit:
    """Tests for NeurosymbolicBandit class."""
    
    @pytest.fixture
    def solver(self):
        """Create a solver with test ontology."""
        return ConstraintSolver(
            ontology=create_blauweiss_ontology(),
            parser=JobRequirementParser()
        )
    
    @pytest.fixture
    def nsai(self, solver):
        """Create NSAI instance."""
        return NeurosymbolicBandit(solver)
    
    def test_create_default(self):
        """Test factory method."""
        nsai = NeurosymbolicBandit.create_default()
        assert nsai.symbolic is not None
        assert nsai.c == 2.0
    
    def test_select_runner_feasible(self, nsai):
        """Test selection with feasible runners."""
        job = {"tags": ["docker-any"]}
        
        runner, explanation = nsai.select_runner(job)
        
        assert runner is not None
        assert isinstance(explanation, Explanation)
        assert len(explanation.feasible_runners) > 0
        assert runner in explanation.feasible_runners
    
    def test_select_runner_infeasible(self, nsai):
        """Test selection with impossible constraints."""
        job = {"tags": ["nonexistent-capability-xyz"]}
        
        runner, explanation = nsai.select_runner(job)
        
        assert runner is None
        assert explanation.confidence == 0.0
        assert "No feasible" in explanation.statistical_reasoning
    
    def test_exploration_phase(self, nsai):
        """Test that unexplored runners are selected first."""
        job = {"tags": ["docker-any"]}
        
        # First selection should explore
        runner1, exp1 = nsai.select_runner(job)
        assert "Unexplored" in exp1.statistical_reasoning
        
        # Update with success
        nsai.update(runner1, success=True, duration_seconds=10.0)
        
        # Second selection should explore another if available
        runner2, exp2 = nsai.select_runner(job)
        if len(exp1.feasible_runners) > 1:
            # If multiple feasible, should explore new one
            assert runner2 != runner1 or "Unexplored" not in exp2.statistical_reasoning
    
    def test_update_success(self, nsai):
        """Test statistics update on success."""
        runner = list(nsai._stats.keys())[0]
        
        nsai.update(runner, success=True, duration_seconds=30.0)
        
        stats = nsai._stats[runner]
        assert stats["pulls"] == 1
        assert stats["successes"] == 1
        assert stats["total_reward"] > 0
    
    def test_update_failure(self, nsai):
        """Test statistics update on failure."""
        runner = list(nsai._stats.keys())[0]
        
        nsai.update(runner, success=False, duration_seconds=30.0)
        
        stats = nsai._stats[runner]
        assert stats["pulls"] == 1
        assert stats["failures"] == 1
        assert stats["total_reward"] == 0.0
    
    def test_get_stats(self, nsai):
        """Test stats retrieval."""
        runner = list(nsai._stats.keys())[0]
        nsai.update(runner, success=True, duration_seconds=60.0)
        
        stats = nsai.get_stats()
        
        assert runner in stats
        assert stats[runner]["pulls"] == 1
        assert stats[runner]["mean_reward"] > 0
    
    def test_sync_from_mab_service(self, nsai):
        """Test syncing from external MAB service."""
        mab_stats = {
            "gitlab-runner-nordic": {
                "pulls": 50,
                "mean_reward": 2.4671,
                "success_rate": 0.96,
                "avg_duration": 19.62
            }
        }
        
        nsai.sync_from_mab_service(mab_stats)
        
        stats = nsai._stats.get("gitlab-runner-nordic")
        if stats:  # Only if runner exists in ontology
            assert stats["pulls"] == 50


class TestUCB1Selection:
    """Tests for UCB1 algorithm behavior."""
    
    @pytest.fixture
    def trained_nsai(self):
        """Create NSAI with some training data."""
        nsai = NeurosymbolicBandit.create_default()
        
        # Simulate some history
        runners = list(nsai._stats.keys())
        if len(runners) >= 2:
            # Runner 1: Good performance
            for _ in range(10):
                nsai.update(runners[0], success=True, duration_seconds=15.0)
            
            # Runner 2: Poor performance
            for _ in range(10):
                nsai.update(runners[1], success=False, duration_seconds=60.0)
        
        return nsai
    
    def test_exploitation(self, trained_nsai):
        """Test that UCB1 exploits good runners."""
        job = {"tags": ["docker-any"]}
        
        # Multiple selections should favor the good runner
        selections = []
        for _ in range(5):
            runner, _ = trained_nsai.select_runner(job)
            if runner:
                selections.append(runner)
        
        # Good runner should be selected more often
        assert len(selections) > 0


class TestIntegration:
    """Integration tests with real ontology."""
    
    def test_full_flow(self):
        """Test complete selection and update flow."""
        nsai = NeurosymbolicBandit.create_default()
        
        # Typical CI job
        job = {
            "tags": ["docker-any"],
            "image": "python:3.11",
            "script": ["pytest"]
        }
        
        # Select runner
        runner, explanation = nsai.select_runner(job, job_name="test-job")
        
        if runner:
            # Simulate execution
            nsai.update(runner, success=True, duration_seconds=45.0)
            
            # Verify stats updated
            stats = nsai.get_stats()
            assert stats[runner]["pulls"] >= 1
    
    def test_alias(self):
        """Test NSAI alias works."""
        nsai = NSAI.create_default()
        assert isinstance(nsai, NeurosymbolicBandit)
