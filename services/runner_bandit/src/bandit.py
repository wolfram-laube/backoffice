"""Multi-Armed Bandit algorithms for runner selection.

Supports persistent state via local file or Google Cloud Storage.
"""
import numpy as np
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RunnerStats:
    """Statistics for a single runner arm."""
    pulls: int = 0
    total_reward: float = 0.0
    successes: int = 0
    failures: int = 0
    total_duration: float = 0.0
    rewards: List[float] = field(default_factory=list)

    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.5

    @property
    def avg_duration(self) -> float:
        return self.total_duration / self.pulls if self.pulls > 0 else 0.0


# ---------------------------------------------------------------------------
# State Persistence Backends
# ---------------------------------------------------------------------------
class StateBackend(ABC):
    """Abstract state persistence backend."""

    @abstractmethod
    def load(self) -> Optional[dict]:
        pass

    @abstractmethod
    def save(self, state: dict) -> None:
        pass


class LocalFileBackend(StateBackend):
    """Persist state to local filesystem (ephemeral on Cloud Run)."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> Optional[dict]:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return None

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2))


class GCSBackend(StateBackend):
    """Persist state to Google Cloud Storage (survives restarts)."""

    def __init__(self, bucket_name: str, blob_name: str = "bandit_state.json"):
        from google.cloud import storage
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.blob_name = blob_name
        logger.info(f"GCS backend: gs://{bucket_name}/{blob_name}")

    def load(self) -> Optional[dict]:
        blob = self.bucket.blob(self.blob_name)
        if blob.exists():
            data = json.loads(blob.download_as_text())
            logger.info(f"Loaded state from GCS: {data.get('total_pulls', 0)} observations")
            return data
        logger.info("No existing state in GCS, starting fresh")
        return None

    def save(self, state: dict) -> None:
        blob = self.bucket.blob(self.blob_name)
        blob.upload_from_string(
            json.dumps(state, indent=2),
            content_type="application/json"
        )
        logger.info(f"Saved state to GCS: {state.get('total_pulls', 0)} observations")


def create_backend() -> StateBackend:
    """Factory: create the appropriate state backend."""
    gcs_bucket = os.getenv("BANDIT_GCS_BUCKET")
    if gcs_bucket:
        blob_name = os.getenv("BANDIT_GCS_BLOB", "bandit_state.json")
        return GCSBackend(gcs_bucket, blob_name)
    
    local_path = Path(os.getenv("BANDIT_STATE_FILE", "/tmp/bandit_state.json"))
    logger.warning(f"Using local file backend ({local_path}) - state will NOT survive restarts!")
    return LocalFileBackend(local_path)


# ---------------------------------------------------------------------------
# Bandit Algorithms
# ---------------------------------------------------------------------------
class BaseBandit(ABC):
    """Abstract base class for bandit algorithms."""

    def __init__(self, runners: List[str], backend: Optional[StateBackend] = None):
        self.runners = runners
        self.stats: Dict[str, RunnerStats] = {r: RunnerStats() for r in runners}
        self.total_pulls = 0
        self.backend = backend or create_backend()
        self._load_state()

    @abstractmethod
    def select_runner(self) -> str:
        pass

    def update(self, runner: str, reward: float, success: bool, duration: float):
        stats = self.stats[runner]
        stats.pulls += 1
        stats.total_reward += reward
        stats.rewards.append(reward)
        stats.total_duration += duration
        if success:
            stats.successes += 1
        else:
            stats.failures += 1
        self.total_pulls += 1
        self._save_state()

    def get_stats(self) -> Dict:
        return {
            runner: {
                "pulls": s.pulls,
                "mean_reward": round(s.mean_reward, 4),
                "success_rate": round(s.success_rate, 4),
                "avg_duration": round(s.avg_duration, 2)
            }
            for runner, s in self.stats.items()
        }

    def get_runner_tag(self, runner: str) -> str:
        """Map runner name to GitLab CI tag for dynamic selection."""
        tag_map = {
            "gitlab-runner-nordic": "nordic",
            "Mac Docker Runner": "mac-docker",
            "Mac2 Docker Runner": "mac2-docker",
            "Linux Yoga Docker Runner": "linux-docker",
        }
        return tag_map.get(runner, "docker-any")

    def _state_dict(self) -> dict:
        return {
            "algorithm": self.__class__.__name__,
            "total_pulls": self.total_pulls,
            "runners": {
                r: {
                    "pulls": s.pulls,
                    "total_reward": s.total_reward,
                    "successes": s.successes,
                    "failures": s.failures,
                    "total_duration": s.total_duration,
                }
                for r, s in self.stats.items()
            }
        }

    def _save_state(self):
        try:
            self.backend.save(self._state_dict())
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self):
        try:
            state = self.backend.load()
            if state:
                self.total_pulls = state["total_pulls"]
                for r, data in state["runners"].items():
                    if r in self.stats:
                        s = self.stats[r]
                        s.pulls = data["pulls"]
                        s.total_reward = data["total_reward"]
                        s.successes = data["successes"]
                        s.failures = data["failures"]
                        s.total_duration = data["total_duration"]
                logger.info(f"Restored {self.total_pulls} observations")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    # Legacy compat
    def save_state(self, path: Path):
        self._save_state()

    def load_state(self, path: Path):
        self._load_state()


class UCB1Bandit(BaseBandit):
    """Upper Confidence Bound (UCB1) algorithm."""

    def __init__(self, runners: List[str], c: float = 2.0, **kwargs):
        self.c = c
        super().__init__(runners, **kwargs)

    def select_runner(self) -> str:
        for runner in self.runners:
            if self.stats[runner].pulls == 0:
                return runner

        ucb_values = {}
        for runner in self.runners:
            stats = self.stats[runner]
            exploitation = stats.mean_reward
            exploration = self.c * np.sqrt(np.log(self.total_pulls) / stats.pulls)
            ucb_values[runner] = exploitation + exploration

        return max(ucb_values, key=ucb_values.get)


class ThompsonSamplingBandit(BaseBandit):
    """Thompson Sampling with Beta-Bernoulli model."""

    def __init__(self, runners: List[str], prior_alpha: float = 1.0,
                 prior_beta: float = 1.0, **kwargs):
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        super().__init__(runners, **kwargs)

    def select_runner(self) -> str:
        samples = {}
        for runner in self.runners:
            stats = self.stats[runner]
            alpha = self.prior_alpha + stats.successes
            beta = self.prior_beta + stats.failures
            samples[runner] = np.random.beta(alpha, beta)
        return max(samples, key=samples.get)


class EpsilonGreedyBandit(BaseBandit):
    """Epsilon-Greedy (baseline)."""

    def __init__(self, runners: List[str], epsilon: float = 0.1, **kwargs):
        self.epsilon = epsilon
        super().__init__(runners, **kwargs)

    def select_runner(self) -> str:
        if np.random.random() < self.epsilon:
            return np.random.choice(self.runners)
        if self.total_pulls == 0:
            return np.random.choice(self.runners)
        return max(self.runners, key=lambda r: self.stats[r].mean_reward)


def calculate_reward(success: bool, duration: float, cost_per_hour: float = 0.0) -> float:
    """Reward = success / (duration_minutes + cost_penalty + ε)."""
    if not success:
        return 0.0
    duration_minutes = duration / 60.0
    cost_penalty = cost_per_hour * (duration / 3600.0)
    return 1.0 / (duration_minutes + cost_penalty + 0.1)
