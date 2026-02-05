"""
Tests for Constraint Satisfaction Module (#24)

pytest tests/test_csp.py -v
"""

import pytest
from nsai.ontology import RunnerOntology
from nsai.parser import JobRequirementParser
from nsai.csp import ConstraintSolver, SelectionResult
from nsai.csp.constraint_solver import SolverStatus


class TestSelectionResult:
    """Tests for SelectionResult dataclass."""
    
    def test_is_feasible(self):
        result = SelectionResult(
            status=SolverStatus.FEASIBLE,
            feasible_runners=["r1"]
        )
        assert result.is_feasible is True
        
        result2 = SelectionResult(status=SolverStatus.INFEASIBLE)
        assert result2.is_feasible is False
    
    def test_best_runner(self):
        result = SelectionResult(
            status=SolverStatus.FEASIBLE,
            ranked_runners=[("r1", 1.0), ("r2", 0.5)]
        )
        assert result.best_runner == "r1"
        
        empty_result = SelectionResult(status=SolverStatus.INFEASIBLE)
        assert empty_result.best_runner is None


class TestConstraintSolver:
    """Tests for ConstraintSolver class."""
    
    @pytest.fixture
    def solver(self):
        ontology = RunnerOntology()
        ontology.add_runner("docker-runner", capabilities=["docker", "linux"])
        ontology.add_runner("gpu-runner", capabilities=["docker", "linux", "gpu"])
        ontology.add_runner("shell-runner", capabilities=["shell", "macos"])
        
        return ConstraintSolver(
            ontology=ontology,
            parser=JobRequirementParser()
        )
    
    def test_solve_simple(self, solver):
        job = {"tags": ["docker-any"]}
        result = solver.solve(job, "test")
        
        assert result.is_feasible
        assert "docker-runner" in result.feasible_runners
        assert "gpu-runner" in result.feasible_runners
        assert "shell-runner" not in result.feasible_runners
    
    def test_solve_with_requirements(self, solver):
        job = {"tags": ["docker-any"], "image": "nvidia/cuda:11.8"}
        result = solver.solve(job, "test")
        
        assert result.is_feasible
        # GPU runner should rank higher due to preference match
        assert result.ranked_runners[0][0] == "gpu-runner"
    
    def test_solve_infeasible(self, solver):
        job = {"tags": ["kubernetes"]}  # No k8s runner
        result = solver.solve(job, "test")
        
        assert not result.is_feasible
        assert result.status == SolverStatus.INFEASIBLE
        assert len(result.feasible_runners) == 0
    
    def test_solve_excludes_offline(self, solver):
        solver.ontology.runners["docker-runner"].online = False
        
        job = {"tags": ["docker-any"]}
        result = solver.solve(job, "test")
        
        assert "docker-runner" not in result.feasible_runners
        assert "docker-runner" in result.pruned_runners
    
    def test_solve_include_offline(self, solver):
        solver.ontology.runners["docker-runner"].online = False
        
        job = {"tags": ["docker-any"]}
        result = solver.solve(job, "test", include_offline=True)
        
        assert "docker-runner" in result.feasible_runners
    
    def test_solve_batch(self, solver):
        jobs = {
            "job1": {"tags": ["docker-any"]},
            "job2": {"tags": ["shell"]}
        }
        results = solver.solve_batch(jobs)
        
        assert "job1" in results
        assert "job2" in results
        assert results["job1"].is_feasible
        assert results["job2"].is_feasible
    
    def test_solve_time_measured(self, solver):
        job = {"tags": ["docker-any"]}
        result = solver.solve(job, "test")
        
        assert result.solve_time_ms > 0
        assert result.solve_time_ms < 1000  # Should be fast
    
    def test_explanation_generated(self, solver):
        job = {"tags": ["docker-any"]}
        result = solver.solve(job, "test")
        
        assert result.explanation
        assert "docker" in result.explanation.lower()
    
    def test_get_runner_recommendation(self, solver):
        job = {"tags": ["docker-any"]}
        runner = solver.get_runner_recommendation(job, "test")
        
        assert runner is not None
        assert runner in ["docker-runner", "gpu-runner"]


class TestIntegration:
    """Integration tests across all modules."""
    
    def test_full_pipeline(self):
        # Create ontology with realistic runners
        ontology = RunnerOntology()
        ontology.add_runner(
            "gitlab-runner-nordic",
            capabilities=["docker", "shell", "gcp", "nordic", "linux"],
            cost_per_minute=0.01
        )
        ontology.add_runner(
            "mac-local",
            capabilities=["shell", "macos"],
            cost_per_minute=0.0,
            online=False
        )
        
        parser = JobRequirementParser()
        solver = ConstraintSolver(ontology, parser)
        
        # Parse a real-world-like job
        job = {
            "tags": ["docker-any"],
            "image": "python:3.11-slim",
            "services": ["postgres:15"],
            "timeout": "30m"
        }
        
        result = solver.solve(job, "test-job")
        
        assert result.is_feasible
        assert result.best_runner == "gitlab-runner-nordic"
        assert result.requirements.timeout_seconds == 30 * 60
    
    def test_yaml_to_selection(self):
        ontology = RunnerOntology()
        ontology.add_runner("r1", capabilities=["docker", "linux"])
        ontology.add_runner("r2", capabilities=["shell", "macos"])
        
        parser = JobRequirementParser()
        solver = ConstraintSolver(ontology, parser)
        
        yaml_content = """
stages:
  - test

unit-test:
  stage: test
  tags:
    - docker-any
  image: python:3.11
  script:
    - pytest
"""
        
        jobs = parser.parse_yaml(yaml_content)
        results = solver.solve_batch({
            name: {"tags": reqs.tags} 
            for name, reqs in jobs.items()
        })
        
        assert results["unit-test"].is_feasible
        assert results["unit-test"].best_runner == "r1"
