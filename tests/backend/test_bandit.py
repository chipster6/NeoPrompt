import random
import types
import math
from typing import Dict

import pytest

from backend.app.bandit import epsilon_greedy_select, BanditConfig
from backend.app.recipes import RecipeModel


def mk_recipe(rid: str) -> RecipeModel:
    return RecipeModel(id=rid, assistant="chatgpt", category="coding", operators=["noop"], hparams={})


def seeded_rng(seed: int = 1234) -> random.Random:
    rng = random.Random(seed)
    return rng


def test_cold_start_prefers_under_sampled():
    candidates = [mk_recipe("r1"), mk_recipe("r2"), mk_recipe("r3")]
    stats: Dict[str, Dict[str, float]] = {
        "r1": {"sample_count": 1, "reward_sum": 0.9},
        "r2": {"sample_count": 0, "reward_sum": 0.0},  # under-sampled
        "r3": {"sample_count": 1, "reward_sum": 0.2},
    }
    config = BanditConfig(min_initial_samples=1, optimistic_initial_value=0.0)
    r, prop, policy, explored = epsilon_greedy_select(candidates, stats, epsilon=0.0, config=config, rng=seeded_rng())
    assert policy == "coldstart"
    assert explored is True
    assert r.id in {"r2"}


def test_epsilon_one_explores_uniformly():
    candidates = [mk_recipe("a"), mk_recipe("b"), mk_recipe("c")]
    stats: Dict[str, Dict[str, float]] = {}
    config = BanditConfig(min_initial_samples=0, optimistic_initial_value=0.0)
    rng = seeded_rng(42)
    seen = set()
    for _ in range(50):
        r, prop, policy, explored = epsilon_greedy_select(candidates, stats, epsilon=1.0, config=config, rng=rng)
        assert policy == "explore"
        assert explored is True
        seen.add(r.id)
    assert seen == {"a", "b", "c"}


def test_epsilon_zero_exploits_best_mean():
    candidates = [mk_recipe("x"), mk_recipe("y")] 
    stats = {
        "x": {"sample_count": 10, "reward_sum": 7.0},  # mean 0.7
        "y": {"sample_count": 10, "reward_sum": 6.0},  # mean 0.6
    }
    config = BanditConfig(min_initial_samples=0, optimistic_initial_value=0.0)
    rng = seeded_rng(7)
    for _ in range(10):
        r, prop, policy, explored = epsilon_greedy_select(candidates, stats, epsilon=0.0, config=config, rng=rng)
        assert policy == "exploit"
        assert explored is False
        assert r.id == "x"


def test_optimistic_initial_value_affects_scores():
    candidates = [mk_recipe("x"), mk_recipe("y")]
    stats = {
        "x": {"sample_count": 0, "reward_sum": 0.0},  # unseen
        "y": {"sample_count": 5, "reward_sum": 2.0},   # mean 0.4
    }
    config = BanditConfig(min_initial_samples=0, optimistic_initial_value=0.6)
    r, prop, policy, explored = epsilon_greedy_select(candidates, stats, epsilon=0.0, config=config, rng=seeded_rng(1))
    # With optimistic prior 0.6, x should be chosen over y's 0.4 during exploit
    assert policy == "exploit"
    assert r.id == "x"


def test_random_tie_break():
    candidates = [mk_recipe("x"), mk_recipe("y"), mk_recipe("z")]
    stats = {
        "x": {"sample_count": 10, "reward_sum": 5.0},  # 0.5
        "y": {"sample_count": 10, "reward_sum": 5.0},  # 0.5
        "z": {"sample_count": 10, "reward_sum": 5.0},  # 0.5
    }
    rng = seeded_rng(99)
    config = BanditConfig(min_initial_samples=0, optimistic_initial_value=0.0)
    seen = set()
    for _ in range(30):
        r, prop, policy, explored = epsilon_greedy_select(candidates, stats, epsilon=0.0, config=config, rng=rng)
        assert policy == "exploit"
        seen.add(r.id)
    # With tie-break, eventually see more than one id
    assert len(seen) >= 2
