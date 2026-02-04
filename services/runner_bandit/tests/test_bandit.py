"""Unit tests for bandit algorithms."""
import pytest
import numpy as np
from src.bandit import UCB1Bandit, ThompsonSamplingBandit, EpsilonGreedyBandit, calculate_reward


class TestUCB1Bandit:
    def test_initial_exploration(self):
        """Each runner should be tried once before exploitation."""
        bandit = UCB1Bandit(["A", "B", "C"])
        
        selected = set()
        for _ in range(3):
            runner = bandit.select_runner()
            selected.add(runner)
            bandit.update(runner, 0.5, True, 10.0)
        
        assert selected == {"A", "B", "C"}
    
    def test_exploitation_after_exploration(self):
        """Best runner should be selected more often after exploration."""
        bandit = UCB1Bandit(["good", "bad"], c=0.1)  # Low exploration
        
        # Initialize both
        bandit.update("good", 1.0, True, 5.0)
        bandit.update("bad", 0.1, True, 50.0)
        
        # Run many selections
        selections = [bandit.select_runner() for _ in range(100)]
        
        assert selections.count("good") > selections.count("bad")


class TestThompsonSampling:
    def test_posterior_update(self):
        """Posterior should reflect observed successes/failures."""
        bandit = ThompsonSamplingBandit(["A", "B"])
        
        # A always succeeds
        for _ in range(10):
            bandit.update("A", 1.0, True, 10.0)
        
        # B always fails
        for _ in range(10):
            bandit.update("B", 0.0, False, 10.0)
        
        assert bandit.stats["A"].success_rate > 0.9
        assert bandit.stats["B"].success_rate < 0.1


class TestRewardCalculation:
    def test_success_reward(self):
        """Successful jobs should have positive reward."""
        reward = calculate_reward(True, 60.0, 0.0)
        assert reward > 0
    
    def test_failure_zero_reward(self):
        """Failed jobs should have zero reward."""
        reward = calculate_reward(False, 60.0, 0.0)
        assert reward == 0.0
    
    def test_faster_is_better(self):
        """Faster jobs should have higher reward."""
        fast = calculate_reward(True, 30.0, 0.0)
        slow = calculate_reward(True, 300.0, 0.0)
        assert fast > slow
    
    def test_cost_penalty(self):
        """Higher cost should reduce reward."""
        free = calculate_reward(True, 60.0, 0.0)
        costly = calculate_reward(True, 60.0, 1.0)
        assert free > costly
