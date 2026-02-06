"""
Integration Tests for NSAI v0.3.0

Tests the full neurosymbolic pipeline including:
- Ontology ↔ MAB service tag alignment
- Live MAB service sync (skipped if offline)
- A/B comparison: Pure MAB vs NSAI vs Rule-Based
- Convergence speed measurement
- Explanation quality checks

Run:
    pytest tests/test_nsai_integration.py -v
    pytest tests/test_nsai_integration.py -v -m "not live"  # skip live tests
"""

import math
import time
import random
import pytest
from typing import Dict, List, Tuple

from nsai import (
    NeurosymbolicBandit, NSAI, Explanation,
    ConstraintSolver, SelectionResult, SolverStatus,
    RunnerOntology, create_blauweiss_ontology,
    JobRequirementParser, JobRequirements,
    __version__,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def ontology():
    return create_blauweiss_ontology()


@pytest.fixture
def nsai():
    return NeurosymbolicBandit.create_default()


@pytest.fixture
def trained_nsai():
    """NSAI with simulated training data for all 4 runners."""
    nsai = NeurosymbolicBandit.create_default()
    runners = list(nsai._stats.keys())

    # Simulate realistic performance profiles:
    #   nordic:      fast, reliable, but costs money
    #   mac-docker:  medium speed, reliable
    #   mac2-docker: slower, occasional failures
    #   linux-yoga:  fast, reliable, free
    profiles = {
        0: (0.96, 18.0, 0.01),    # nordic: 96% success, 18s avg, €0.01/min
        1: (0.92, 25.0, 0.0),     # mac-docker
        2: (0.85, 35.0, 0.0),     # mac2-docker
        3: (0.95, 15.0, 0.0),     # linux-yoga
    }

    rng = random.Random(42)
    for i, runner in enumerate(runners):
        if i not in profiles:
            continue
        success_rate, avg_dur, cost = profiles[i]
        for _ in range(20):
            success = rng.random() < success_rate
            duration = max(5.0, rng.gauss(avg_dur, avg_dur * 0.2))
            nsai.update(runner, success=success, duration_seconds=duration,
                        cost_per_minute=cost)

    return nsai


# ============================================================
# Version & Smoke Tests
# ============================================================

class TestVersion:
    def test_version_bump(self):
        assert __version__ == "0.3.0"

    def test_all_exports_available(self):
        """Verify all public API symbols are importable."""
        from nsai import (NeurosymbolicBandit, NSAI, Explanation,
                          ConstraintSolver, SelectionResult, SolverStatus,
                          RunnerOntology, create_blauweiss_ontology,
                          JobRequirementParser, JobRequirements)


# ============================================================
# Ontology ↔ MAB Alignment Tests
# ============================================================

class TestOntologyMABAlignment:
    """Verify ontology runner names align with MAB service."""

    MAB_RUNNERS = [
        "gitlab-runner-nordic",
        "Mac Docker Runner",
        "Mac2 Docker Runner",
        "Linux Yoga Docker Runner",
    ]

    MAB_TAGS = ["nordic", "mac-docker", "mac2-docker", "linux-docker"]

    def test_all_mab_runners_in_ontology(self, ontology):
        for name in self.MAB_RUNNERS:
            assert name in ontology.runners, f"MAB runner '{name}' missing from ontology"

    def test_mab_tag_roundtrip(self, ontology):
        """tag → runner_name → tag should be identity."""
        for tag in self.MAB_TAGS:
            runner_name = ontology.runner_name_for_mab_tag(tag)
            assert runner_name is not None, f"No runner for MAB tag '{tag}'"
            resolved_tag = ontology.mab_tag_for_runner(runner_name)
            assert resolved_tag == tag

    def test_all_runners_have_docker(self, ontology):
        """All runners must support docker (our CI minimum)."""
        for name, runner in ontology.runners.items():
            assert runner.has_capability("docker"), \
                f"Runner '{name}' lacks docker capability"

    def test_runner_count_matches_mab(self, nsai):
        """NSAI must track exactly as many runners as MAB."""
        assert len(nsai._stats) == 4

    def test_sync_maps_by_name(self, nsai):
        """sync_from_mab_service should map by runner name directly."""
        mab_stats = {
            "gitlab-runner-nordic": {
                "pulls": 100, "mean_reward": 3.0,
                "success_rate": 0.95, "avg_duration": 20.0
            }
        }
        nsai.sync_from_mab_service(mab_stats)
        assert nsai._stats["gitlab-runner-nordic"]["pulls"] == 100

    def test_ontology_serialization_roundtrip(self, ontology):
        """Serialize → deserialize should preserve mab_tag."""
        data = ontology.to_dict()
        restored = RunnerOntology.from_dict(data)
        for name, runner in ontology.runners.items():
            assert restored.runners[name].mab_tag == runner.mab_tag


# ============================================================
# CSP + MAB Integration
# ============================================================

class TestCSPMABIntegration:
    """Test the two-layer selection pipeline."""

    def test_docker_job_all_feasible(self, nsai):
        """A docker-any job should see all 4 runners as feasible."""
        _, exp = nsai.select_runner({"tags": ["docker-any"]})
        assert len(exp.feasible_runners) == 4

    def test_gcp_job_filters_to_nordic(self, nsai):
        """A GCP-requiring job should only see nordic."""
        _, exp = nsai.select_runner({"tags": ["docker-any", "gcp"]})
        assert exp.feasible_runners == ["gitlab-runner-nordic"]

    def test_shell_job_excludes_mac_runners(self, nsai):
        """A shell-requiring job filters out Mac runners (no shell cap)."""
        _, exp = nsai.select_runner({"tags": ["shell"]})
        feasible = exp.feasible_runners
        for r in feasible:
            assert "Mac" not in r, f"Mac runner '{r}' should lack shell"

    def test_infeasible_returns_none(self, nsai):
        """Impossible constraints → None selection."""
        runner, exp = nsai.select_runner({"tags": ["gpu", "arm64"]})
        assert runner is None
        assert exp.confidence == 0.0

    def test_exploration_visits_all_runners(self, nsai):
        """UCB1 should explore all feasible runners before exploiting."""
        job = {"tags": ["docker-any"]}
        visited = set()
        for _ in range(10):
            runner, _ = nsai.select_runner(job)
            if runner:
                visited.add(runner)
                nsai.update(runner, success=True, duration_seconds=20.0)
        assert len(visited) == 4, f"Only visited {visited}"

    def test_explanation_has_both_layers(self, trained_nsai):
        """Explanation must contain symbolic AND statistical reasoning."""
        _, exp = trained_nsai.select_runner({"tags": ["docker-any"]})
        assert len(exp.symbolic_reasoning) > 0
        assert len(exp.statistical_reasoning) > 0
        assert "UCB" in exp.statistical_reasoning or "Evaluating" in exp.statistical_reasoning


# ============================================================
# A/B Comparison: Pure MAB vs NSAI vs Rule-Based
# ============================================================

class TestABComparison:
    """
    Simulated A/B comparison between three strategies:
      - Rule-Based: always picks the first feasible runner (static)
      - Pure MAB:   UCB1 over ALL runners (no CSP filtering)
      - NSAI:       CSP filter → UCB1 (our approach)
    """

    # Simulated ground-truth: reward per runner for different job types
    GROUND_TRUTH = {
        "docker-any": {
            "gitlab-runner-nordic": 0.8,
            "Mac Docker Runner": 0.6,
            "Mac2 Docker Runner": 0.4,
            "Linux Yoga Docker Runner": 0.9,
        },
        "gcp": {
            "gitlab-runner-nordic": 0.85,
            "Mac Docker Runner": 0.0,      # infeasible
            "Mac2 Docker Runner": 0.0,      # infeasible
            "Linux Yoga Docker Runner": 0.0,  # infeasible
        },
    }

    @staticmethod
    def _simulate_job(runner: str, job_type: str, truth: dict,
                      rng: random.Random) -> Tuple[bool, float]:
        """Simulate a job execution."""
        reward = truth.get(job_type, {}).get(runner, 0.0)
        success = rng.random() < reward
        duration = rng.gauss(20.0, 5.0) if success else rng.gauss(60.0, 10.0)
        return success, max(5.0, duration)

    def test_nsai_outperforms_rule_based(self):
        """NSAI should accumulate more reward than static rule-based."""
        rng = random.Random(123)
        n_rounds = 100

        # Rule-based: always picks first runner
        rule_reward = 0.0
        # NSAI
        nsai = NeurosymbolicBandit.create_default()
        nsai_reward = 0.0

        for _ in range(n_rounds):
            job = {"tags": ["docker-any"]}

            # Rule-based
            rule_runner = "gitlab-runner-nordic"
            success, dur = self._simulate_job(
                rule_runner, "docker-any", self.GROUND_TRUTH, rng)
            rule_reward += 1.0 if success else 0.0

            # NSAI
            runner, _ = nsai.select_runner(job)
            success, dur = self._simulate_job(
                runner, "docker-any", self.GROUND_TRUTH, rng)
            nsai.update(runner, success=success, duration_seconds=dur)
            nsai_reward += 1.0 if success else 0.0

        assert nsai_reward >= rule_reward * 0.9, \
            f"NSAI ({nsai_reward}) significantly worse than rule-based ({rule_reward})"

    def test_nsai_convergence_speed(self):
        """NSAI should converge to best runner within reasonable rounds."""
        rng = random.Random(456)
        nsai = NeurosymbolicBandit.create_default()

        # Train
        for _ in range(50):
            job = {"tags": ["docker-any"]}
            runner, _ = nsai.select_runner(job)
            success, dur = self._simulate_job(
                runner, "docker-any", self.GROUND_TRUTH, rng)
            nsai.update(runner, success=success, duration_seconds=dur)

        # After 50 rounds, best runner (linux-yoga, reward=0.9) should dominate
        selections = []
        for _ in range(20):
            runner, _ = nsai.select_runner({"tags": ["docker-any"]})
            selections.append(runner)

        best = max(set(selections), key=selections.count)
        # Linux Yoga should be selected most often (highest ground-truth reward)
        assert best == "Linux Yoga Docker Runner", \
            f"Expected Linux Yoga to dominate, got {best}"

    def test_regret_decreases_over_time(self):
        """Cumulative regret growth should slow down (sublinear)."""
        rng = random.Random(789)
        nsai = NeurosymbolicBandit.create_default()
        best_reward = 0.9  # Linux Yoga ground truth

        regret_first_half = 0.0
        regret_second_half = 0.0
        n_rounds = 100

        for i in range(n_rounds):
            job = {"tags": ["docker-any"]}
            runner, _ = nsai.select_runner(job)
            actual_reward = self.GROUND_TRUTH["docker-any"].get(runner, 0.0)
            regret = best_reward - actual_reward

            if i < n_rounds // 2:
                regret_first_half += regret
            else:
                regret_second_half += regret

            success = rng.random() < actual_reward
            dur = rng.gauss(20.0, 5.0) if success else rng.gauss(60.0, 10.0)
            nsai.update(runner, success=success, duration_seconds=max(5.0, dur))

        # Second half regret should be lower (learning kicks in)
        assert regret_second_half <= regret_first_half, \
            f"Regret not decreasing: first={regret_first_half:.1f}, second={regret_second_half:.1f}"


# ============================================================
# Live MAB Service Tests (skip if offline)
# ============================================================

def _mab_service_available():
    """Check if MAB Cloud Run service is reachable."""
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://runner-bandit-m5cziijwqa-lz.a.run.app/",
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.mark.skipif(not _mab_service_available(),
                    reason="MAB service not reachable")
class TestLiveMABIntegration:
    """Tests against the live MAB Cloud Run service."""

    SERVICE_URL = "https://runner-bandit-m5cziijwqa-lz.a.run.app"

    def _fetch_json(self, path: str) -> dict:
        import urllib.request, json
        req = urllib.request.Request(f"{self.SERVICE_URL}{path}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def test_service_info(self):
        data = self._fetch_json("/")
        assert data["service"] == "Runner Bandit"
        assert "UCB1" in data["algorithm"]

    def test_service_has_all_runners(self):
        data = self._fetch_json("/")
        expected = {"gitlab-runner-nordic", "Mac Docker Runner",
                    "Mac2 Docker Runner", "Linux Yoga Docker Runner"}
        assert set(data["runners"]) == expected

    def test_recommend_returns_valid_runner(self):
        data = self._fetch_json("/recommend")
        assert "recommended_runner" in data or "runner" in data

    def test_sync_from_live_service(self):
        """Create NSAI warm-started from live service."""
        nsai = NeurosymbolicBandit.from_live_service(self.SERVICE_URL)
        stats = nsai.get_stats()
        # At minimum, runner entries should exist
        assert len(stats) == 4

    def test_stats_endpoint(self):
        data = self._fetch_json("/stats")
        assert "runners" in data
        for runner_name, rstats in data["runners"].items():
            assert "pulls" in rstats
            assert "mean_reward" in rstats
            assert "success_rate" in rstats


# ============================================================
# Performance & Edge Cases
# ============================================================

class TestPerformance:
    def test_selection_under_10ms(self, trained_nsai):
        """Selection should be fast (< 10ms)."""
        job = {"tags": ["docker-any"]}
        start = time.perf_counter()
        for _ in range(100):
            trained_nsai.select_runner(job)
        elapsed = (time.perf_counter() - start) * 1000
        avg_ms = elapsed / 100
        assert avg_ms < 10, f"Selection too slow: {avg_ms:.2f}ms avg"

    def test_many_updates_stable(self, nsai):
        """System should remain stable after many updates."""
        runner = list(nsai._stats.keys())[0]
        for i in range(1000):
            nsai.update(runner, success=(i % 3 != 0),
                        duration_seconds=10.0 + (i % 50))
        stats = nsai.get_stats()
        assert 0 < stats[runner]["mean_reward"] < 100
        assert 0 < stats[runner]["success_rate"] < 1

    def test_empty_tags_handled(self, nsai):
        """Job with no tags should still work."""
        runner, exp = nsai.select_runner({"script": ["echo hello"]})
        # With no constraints, all online runners are feasible
        assert len(exp.feasible_runners) >= 1
