"""
Integration Tests for NSAI v0.4.0

Tests the full neurosymbolic pipeline with 11-runner fleet:
- Docker (4): Nordic, Mac, Mac2, Linux Yoga
- Shell  (5): Nordic, Mac, Mac2, Linux Yoga Shell, Linux Yoga Docker
- K8s    (3): Mac, Mac2, Linux Yoga (Nordic K8s offline)

See INF-002 for fleet architecture.

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
# Constants — Single Source of Truth for runner fleet
# ============================================================

TOTAL_RUNNERS = 11
ONLINE_RUNNERS_COUNT = 10  # Nordic K8s is offline

DOCKER_RUNNERS = [
    "gitlab-runner-nordic",
    "Mac Docker Runner",
    "Mac2 Docker Runner",
    "Linux Yoga Docker Runner",
]

# Runners with shell capability
SHELL_CAPABLE = [
    "gitlab-runner-nordic",        # docker+shell
    "Linux Yoga Docker Runner",    # docker+shell
    "Mac Shell Runner",
    "Mac2 Shell Runner",
    "Linux Yoga Shell Runner",
]

K8S_RUNNERS_ONLINE = [
    "Mac K8s Runner",
    "Mac2 K8s Runner",
    "Linux Yoga K8s Runner",
]

ALL_MAB_TAGS = [
    "nordic", "mac-docker", "mac2-docker", "linux-docker",
    "mac-shell", "mac2-shell", "linux-shell",
    "mac-k8s", "mac2-k8s", "linux-k8s", "nordic-k8s",
]

# Runners on the live MAB Cloud Run service (not yet updated to 11)
LIVE_MAB_RUNNERS = [
    "gitlab-runner-nordic",
    "Mac Docker Runner",
    "Mac2 Docker Runner",
    "Linux Yoga Docker Runner",
]


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
    """NSAI with simulated training data for all online runners."""
    nsai = NeurosymbolicBandit.create_default()

    profiles = {
        "gitlab-runner-nordic":     (0.96, 18.0, 0.01),
        "Mac Docker Runner":        (0.92, 25.0, 0.0),
        "Mac2 Docker Runner":       (0.85, 35.0, 0.0),
        "Linux Yoga Docker Runner": (0.95, 15.0, 0.0),
        "Mac Shell Runner":         (0.90, 20.0, 0.0),
        "Mac2 Shell Runner":        (0.88, 22.0, 0.0),
        "Linux Yoga Shell Runner":  (0.94, 12.0, 0.0),
        "Mac K8s Runner":           (0.80, 40.0, 0.0),
        "Mac2 K8s Runner":          (0.78, 45.0, 0.0),
        "Linux Yoga K8s Runner":    (0.82, 38.0, 0.0),
    }

    rng = random.Random(42)
    for runner_name, (success_rate, avg_dur, cost) in profiles.items():
        for _ in range(20):
            success = rng.random() < success_rate
            duration = max(5.0, rng.gauss(avg_dur, avg_dur * 0.2))
            nsai.update(runner_name, success=success, duration_seconds=duration,
                        cost_per_minute=cost)

    return nsai


# ============================================================
# Version & Smoke
# ============================================================

class TestVersion:
    def test_version_bump(self):
        assert __version__ == "0.4.0"

    def test_all_exports_available(self):
        from nsai import (NeurosymbolicBandit, NSAI, Explanation,
                          ConstraintSolver, SelectionResult, SolverStatus,
                          RunnerOntology, create_blauweiss_ontology,
                          JobRequirementParser, JobRequirements)


# ============================================================
# Ontology Completeness
# ============================================================

class TestOntologyCompleteness:

    def test_total_runner_count(self, ontology):
        assert len(ontology.runners) == TOTAL_RUNNERS

    def test_runner_ids_populated(self, ontology):
        for name, runner in ontology.runners.items():
            assert runner.runner_id is not None, f"'{name}' missing runner_id"

    def test_docker_runners_have_docker(self, ontology):
        for name in DOCKER_RUNNERS:
            assert ontology.runners[name].has_capability("docker")

    def test_shell_runners_have_shell(self, ontology):
        for name in SHELL_CAPABLE:
            assert ontology.runners[name].has_capability("shell")

    def test_k8s_runners_have_kubernetes(self, ontology):
        for name in K8S_RUNNERS_ONLINE + ["Nordic K8s Runner"]:
            assert ontology.runners[name].has_capability("kubernetes")

    def test_nordic_k8s_offline(self, ontology):
        assert ontology.runners["Nordic K8s Runner"].online is False

    def test_online_count(self, ontology):
        online = [n for n, r in ontology.runners.items() if r.online]
        assert len(online) == ONLINE_RUNNERS_COUNT

    def test_every_runner_has_executor(self, ontology):
        executors = {"docker", "shell", "kubernetes"}
        for name, runner in ontology.runners.items():
            caps = {c.name for c in runner.capabilities}
            assert caps & executors, f"'{name}' has no executor cap (has: {caps})"


# ============================================================
# Ontology ↔ MAB Tag Alignment
# ============================================================

class TestOntologyMABAlignment:

    def test_all_runners_have_mab_tag(self, ontology):
        for name, runner in ontology.runners.items():
            assert runner.mab_tag, f"'{name}' has empty mab_tag"

    def test_mab_tag_roundtrip(self, ontology):
        for tag in ALL_MAB_TAGS:
            runner_name = ontology.runner_name_for_mab_tag(tag)
            assert runner_name is not None, f"No runner for MAB tag '{tag}'"
            assert ontology.mab_tag_for_runner(runner_name) == tag

    def test_mab_tags_unique(self, ontology):
        tags = [r.mab_tag for r in ontology.runners.values()]
        assert len(tags) == len(set(tags))

    def test_nsai_stats_count(self, nsai):
        assert len(nsai._stats) == TOTAL_RUNNERS

    def test_serialization_roundtrip(self, ontology):
        data = ontology.to_dict()
        restored = RunnerOntology.from_dict(data)
        for name, runner in ontology.runners.items():
            assert restored.runners[name].mab_tag == runner.mab_tag
            assert restored.runners[name].runner_id == runner.runner_id

    def test_sync_maps_by_name(self, nsai):
        mab_stats = {
            "gitlab-runner-nordic": {
                "pulls": 100, "mean_reward": 3.0,
                "success_rate": 0.95, "avg_duration": 20.0
            }
        }
        nsai.sync_from_mab_service(mab_stats)
        assert nsai._stats["gitlab-runner-nordic"]["pulls"] == 100


# ============================================================
# Parser Tag Mappings
# ============================================================

class TestParserTagMappings:

    def test_docker_any(self):
        reqs = JobRequirementParser().parse({"tags": ["docker-any"]})
        assert "docker" in reqs.required_capabilities

    def test_shell_any(self):
        reqs = JobRequirementParser().parse({"tags": ["shell-any"]})
        assert "shell" in reqs.required_capabilities

    def test_k8s_any(self):
        reqs = JobRequirementParser().parse({"tags": ["k8s-any"]})
        assert "kubernetes" in reqs.required_capabilities

    def test_any_runner_no_constraints(self):
        reqs = JobRequirementParser().parse({"tags": ["any-runner"]})
        # any-runner → [] → no executor constraint from this tag
        assert "any-runner" not in reqs.required_capabilities

    def test_nordic_requires_gcp(self):
        reqs = JobRequirementParser().parse({"tags": ["nordic"]})
        assert "nordic" in reqs.required_capabilities
        assert "gcp" in reqs.required_capabilities

    def test_specific_tag_pins_hardware(self):
        reqs = JobRequirementParser().parse({"tags": ["mac-docker"]})
        assert "docker" in reqs.required_capabilities
        assert "macos" in reqs.required_capabilities


# ============================================================
# CSP + MAB Integration
# ============================================================

class TestCSPMABIntegration:

    def test_docker_job(self, nsai):
        """docker-any → exactly 4 Docker runners."""
        _, exp = nsai.select_runner({"tags": ["docker-any"]})
        assert len(exp.feasible_runners) == len(DOCKER_RUNNERS)
        assert set(exp.feasible_runners) == set(DOCKER_RUNNERS)

    def test_shell_job(self, nsai):
        """shell-any → runners with shell capability."""
        _, exp = nsai.select_runner({"tags": ["shell-any"]})
        assert len(exp.feasible_runners) == len(SHELL_CAPABLE)
        for r in exp.feasible_runners:
            assert nsai.symbolic.ontology.runners[r].has_capability("shell")

    def test_k8s_job(self, nsai):
        """k8s-any → online K8s runners only."""
        _, exp = nsai.select_runner({"tags": ["k8s-any"]})
        assert len(exp.feasible_runners) == len(K8S_RUNNERS_ONLINE)
        assert set(exp.feasible_runners) == set(K8S_RUNNERS_ONLINE)

    def test_gcp_job(self, nsai):
        """GCP-requiring docker job → only Nordic."""
        _, exp = nsai.select_runner({"tags": ["docker-any", "gcp"]})
        assert exp.feasible_runners == ["gitlab-runner-nordic"]

    def test_any_runner(self, nsai):
        """any-runner with no image → all 10 online runners."""
        _, exp = nsai.select_runner({"tags": ["any-runner"]})
        assert len(exp.feasible_runners) == ONLINE_RUNNERS_COUNT

    def test_infeasible(self, nsai):
        runner, exp = nsai.select_runner({"tags": ["gpu", "arm64"]})
        assert runner is None
        assert exp.confidence == 0.0

    def test_explore_docker(self, nsai):
        """UCB1 explores all Docker runners."""
        visited = set()
        for _ in range(10):
            runner, _ = nsai.select_runner({"tags": ["docker-any"]})
            if runner:
                visited.add(runner)
                nsai.update(runner, success=True, duration_seconds=20.0)
        assert visited == set(DOCKER_RUNNERS)

    def test_explore_k8s(self, nsai):
        """UCB1 explores all K8s runners."""
        visited = set()
        for _ in range(10):
            runner, _ = nsai.select_runner({"tags": ["k8s-any"]})
            if runner:
                visited.add(runner)
                nsai.update(runner, success=True, duration_seconds=20.0)
        assert visited == set(K8S_RUNNERS_ONLINE)

    def test_explanation_layers(self, trained_nsai):
        _, exp = trained_nsai.select_runner({"tags": ["docker-any"]})
        assert len(exp.symbolic_reasoning) > 0
        assert len(exp.statistical_reasoning) > 0


# ============================================================
# Cross-Executor Tests
# ============================================================

class TestCrossExecutor:

    def test_docker_k8s_disjoint(self, nsai):
        """No runner should be in both docker-any and k8s-any feasible sets."""
        _, d = nsai.select_runner({"tags": ["docker-any"]})
        _, k = nsai.select_runner({"tags": ["k8s-any"]})
        assert not set(d.feasible_runners) & set(k.feasible_runners)

    def test_docker_shell_overlap(self, nsai):
        """Nordic and Linux Yoga Docker have both docker and shell."""
        _, d = nsai.select_runner({"tags": ["docker-any"]})
        _, s = nsai.select_runner({"tags": ["shell-any"]})
        overlap = set(d.feasible_runners) & set(s.feasible_runners)
        assert len(overlap) >= 2, f"Expected ≥2 docker/shell overlap, got {overlap}"

    def test_mac_any_spans_executors(self, nsai):
        """mac-any finds Mac runners from Docker + Shell + K8s."""
        _, exp = nsai.select_runner({"tags": ["mac-any"]})
        assert len(exp.feasible_runners) >= 3


# ============================================================
# A/B Comparison
# ============================================================

class TestABComparison:

    GROUND_TRUTH = {
        "docker-any": {
            "gitlab-runner-nordic": 0.8,
            "Mac Docker Runner": 0.6,
            "Mac2 Docker Runner": 0.4,
            "Linux Yoga Docker Runner": 0.9,
        },
    }

    @staticmethod
    def _simulate(runner, job_type, truth, rng):
        reward = truth.get(job_type, {}).get(runner, 0.0)
        success = rng.random() < reward
        dur = rng.gauss(20.0, 5.0) if success else rng.gauss(60.0, 10.0)
        return success, max(5.0, dur)

    def test_nsai_vs_rule_based(self):
        rng = random.Random(123)
        rule_reward, nsai_reward = 0.0, 0.0
        nsai = NeurosymbolicBandit.create_default()

        for _ in range(100):
            s, _ = self._simulate("gitlab-runner-nordic", "docker-any",
                                   self.GROUND_TRUTH, rng)
            rule_reward += float(s)
            runner, _ = nsai.select_runner({"tags": ["docker-any"]})
            s, d = self._simulate(runner, "docker-any", self.GROUND_TRUTH, rng)
            nsai.update(runner, success=s, duration_seconds=d)
            nsai_reward += float(s)

        assert nsai_reward >= rule_reward * 0.9

    def test_convergence(self):
        rng = random.Random(456)
        nsai = NeurosymbolicBandit.create_default()
        for _ in range(50):
            runner, _ = nsai.select_runner({"tags": ["docker-any"]})
            s, d = self._simulate(runner, "docker-any", self.GROUND_TRUTH, rng)
            nsai.update(runner, success=s, duration_seconds=d)
        sels = [nsai.select_runner({"tags": ["docker-any"]})[0] for _ in range(20)]
        best = max(set(sels), key=sels.count)
        assert best == "Linux Yoga Docker Runner"

    def test_regret_sublinear(self):
        rng = random.Random(789)
        nsai = NeurosymbolicBandit.create_default()
        reg1, reg2 = 0.0, 0.0
        for i in range(100):
            runner, _ = nsai.select_runner({"tags": ["docker-any"]})
            actual = self.GROUND_TRUTH["docker-any"].get(runner, 0.0)
            (reg1 if i < 50 else reg2).__iadd__(0.9 - actual) if False else None
            if i < 50:
                reg1 += 0.9 - actual
            else:
                reg2 += 0.9 - actual
            s = rng.random() < actual
            d = rng.gauss(20.0, 5.0) if s else rng.gauss(60.0, 10.0)
            nsai.update(runner, success=s, duration_seconds=max(5.0, d))
        assert reg2 <= reg1


# ============================================================
# Live MAB Service (skip if offline)
# ============================================================

def _mab_service_available():
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://runner-bandit-m5cziijwqa-lz.a.run.app/", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


@pytest.mark.skipif(not _mab_service_available(),
                    reason="MAB service not reachable")
class TestLiveMABIntegration:
    """Tests against the live MAB service (still 4 Docker runners)."""

    URL = "https://runner-bandit-m5cziijwqa-lz.a.run.app"

    def _get(self, path):
        import urllib.request, json
        with urllib.request.urlopen(f"{self.URL}{path}", timeout=10) as r:
            return json.loads(r.read())

    def test_service_info(self):
        d = self._get("/")
        assert d["service"] == "Runner Bandit"

    def test_has_docker_runners(self):
        d = self._get("/")
        for name in LIVE_MAB_RUNNERS:
            assert name in d["runners"]

    def test_recommend(self):
        d = self._get("/recommend")
        assert "recommended_runner" in d

    def test_stats(self):
        d = self._get("/stats")
        assert "runners" in d


# ============================================================
# Performance
# ============================================================

class TestPerformance:
    def test_selection_under_10ms(self, trained_nsai):
        start = time.perf_counter()
        for _ in range(100):
            trained_nsai.select_runner({"tags": ["docker-any"]})
        avg_ms = (time.perf_counter() - start) * 10  # *1000/100
        assert avg_ms < 10, f"Too slow: {avg_ms:.2f}ms"

    def test_many_updates_stable(self, nsai):
        runner = list(nsai._stats.keys())[0]
        for i in range(1000):
            nsai.update(runner, success=(i % 3 != 0), duration_seconds=10 + i % 50)
        s = nsai.get_stats()
        assert 0 < s[runner]["mean_reward"] < 100
        assert 0 < s[runner]["success_rate"] < 1

    def test_empty_tags(self, nsai):
        _, exp = nsai.select_runner({"script": ["echo hello"]})
        assert len(exp.feasible_runners) >= 1

    def test_batch_solve(self, nsai):
        results = nsai.symbolic.solve_batch({
            "test:unit": {"tags": ["docker-any"], "image": "python:3.11"},
            "k8s:deploy": {"tags": ["k8s-any"]},
            "billing:build": {"tags": ["shell-any"]},
        })
        assert all(r.is_feasible for r in results.values())
