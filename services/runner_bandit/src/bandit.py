"""Multi-Armed Bandit algorithms for runner selection."""
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List
from abc import ABC, abstractmethod
import json
from pathlib import Path


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


class BaseBandit(ABC):
    """Abstract base class for bandit algorithms."""
    
    def __init__(self, runners: List[str]):
        self.runners = runners
        self.stats: Dict[str, RunnerStats] = {r: RunnerStats() for r in runners}
        self.total_pulls = 0
    
    @abstractmethod
    def select_runner(self) -> str:
        """Select a runner based on the algorithm's policy."""
        pass
    
    def update(self, runner: str, reward: float, success: bool, duration: float):
        """Update statistics after observing outcome."""
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
    
    def get_stats(self) -> Dict:
        """Return current statistics for all runners."""
        return {
            runner: {
                "pulls": s.pulls,
                "mean_reward": round(s.mean_reward, 4),
                "success_rate": round(s.success_rate, 4),
                "avg_duration": round(s.avg_duration, 2)
            }
            for runner, s in self.stats.items()
        }
    
    def save_state(self, path: Path):
        """Persist bandit state to JSON."""
        state = {
            "algorithm": self.__class__.__name__,
            "total_pulls": self.total_pulls,
            "runners": {
                r: {
                    "pulls": s.pulls,
                    "total_reward": s.total_reward,
                    "successes": s.successes,
                    "failures": s.failures,
                    "total_duration": s.total_duration
                }
                for r, s in self.stats.items()
            }
        }
        path.write_text(json.dumps(state, indent=2))
    
    def load_state(self, path: Path):
        """Load bandit state from JSON."""
        if not path.exists():
            return
        state = json.loads(path.read_text())
        self.total_pulls = state["total_pulls"]
        for r, data in state["runners"].items():
            if r in self.stats:
                self.stats[r].pulls = data["pulls"]
                self.stats[r].total_reward = data["total_reward"]
                self.stats[r].successes = data["successes"]
                self.stats[r].failures = data["failures"]
                self.stats[r].total_duration = data["total_duration"]


class UCB1Bandit(BaseBandit):
    """Upper Confidence Bound (UCB1) algorithm.
    
    Balances exploitation (high reward runners) with exploration
    (uncertain runners) using confidence bounds.
    
    UCB1 = mean_reward + c * sqrt(ln(t) / n_i)
    
    Args:
        runners: List of runner identifiers
        c: Exploration parameter (default: 2.0, higher = more exploration)
    """
    
    def __init__(self, runners: List[str], c: float = 2.0):
        super().__init__(runners)
        self.c = c
    
    def select_runner(self) -> str:
        # Ensure each runner is tried at least once
        for runner in self.runners:
            if self.stats[runner].pulls == 0:
                return runner
        
        # UCB1 formula
        ucb_values = {}
        for runner in self.runners:
            stats = self.stats[runner]
            exploitation = stats.mean_reward
            exploration = self.c * np.sqrt(np.log(self.total_pulls) / stats.pulls)
            ucb_values[runner] = exploitation + exploration
        
        return max(ucb_values, key=ucb_values.get)


class ThompsonSamplingBandit(BaseBandit):
    """Thompson Sampling with Beta-Bernoulli model.
    
    Maintains Beta posterior for each runner's success probability.
    Samples from posteriors and selects runner with highest sample.
    
    Args:
        runners: List of runner identifiers
        prior_alpha: Prior successes (default: 1.0)
        prior_beta: Prior failures (default: 1.0)
    """
    
    def __init__(self, runners: List[str], prior_alpha: float = 1.0, prior_beta: float = 1.0):
        super().__init__(runners)
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
    
    def select_runner(self) -> str:
        samples = {}
        for runner in self.runners:
            stats = self.stats[runner]
            alpha = self.prior_alpha + stats.successes
            beta = self.prior_beta + stats.failures
            samples[runner] = np.random.beta(alpha, beta)
        
        return max(samples, key=samples.get)


class EpsilonGreedyBandit(BaseBandit):
    """Epsilon-Greedy algorithm (baseline).
    
    With probability epsilon, explore randomly.
    Otherwise, exploit the best known runner.
    
    Args:
        runners: List of runner identifiers
        epsilon: Exploration probability (default: 0.1)
    """
    
    def __init__(self, runners: List[str], epsilon: float = 0.1):
        super().__init__(runners)
        self.epsilon = epsilon
    
    def select_runner(self) -> str:
        if np.random.random() < self.epsilon:
            return np.random.choice(self.runners)
        
        # Greedy: select runner with highest mean reward
        if self.total_pulls == 0:
            return np.random.choice(self.runners)
        
        return max(self.runners, key=lambda r: self.stats[r].mean_reward)


def calculate_reward(success: bool, duration: float, cost_per_hour: float = 0.0) -> float:
    """Calculate reward for a job execution.
    
    Reward = success / (duration_minutes + cost_penalty)
    
    Args:
        success: Whether job succeeded
        duration: Job duration in seconds
        cost_per_hour: Runner cost in EUR/hour
    
    Returns:
        Reward value (higher is better)
    """
    if not success:
        return 0.0
    
    duration_minutes = duration / 60.0
    cost_penalty = cost_per_hour * (duration / 3600.0)
    
    return 1.0 / (duration_minutes + cost_penalty + 0.1)  # +0.1 to avoid division issues
