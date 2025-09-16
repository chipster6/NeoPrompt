"""Bandit repository, ε-greedy selector, and service integration.

Provides a persistent stats store backed by :class:`BanditStats` along with helpers
for an ε-greedy policy. The selector supports:

* cold start handling via ``min_initial_samples``
* an optimistic initial value for unseen recipes
* random tie-breaking for equal averages
* accounting of explore vs exploit selections
* a small in-process TTL cache for stats
* Prometheus metrics for selection and feedback latency
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import time

from sqlalchemy.orm import Session

from .db import BanditStats
from .recipes import RecipeModel
from .optimizer import _eligible
from . import metrics

logger = logging.getLogger(__name__)


@dataclass
class BanditConfig:
    min_initial_samples: int = 1
    optimistic_initial_value: float = 0.0


class BanditStatsRepository:
    def get_group_stats(self, db: Session, assistant: str, category: str) -> Dict[str, Dict[str, float]]:
        rows = (
            db.query(BanditStats)
            .filter(BanditStats.assistant == assistant, BanditStats.category == category)
            .all()
        )
        stats: Dict[str, Dict[str, float]] = {}
        for r in rows:
            stats[r.recipe_id] = {
                "sample_count": float(r.sample_count or 0),
                "reward_sum": float(r.reward_sum or 0.0),
                "explore_count": float(r.explore_count or 0),
                "exploit_count": float(r.exploit_count or 0),
            }
        return stats

    def _get_or_create(self, db: Session, assistant: str, category: str, recipe_id: str) -> BanditStats:
        row = (
            db.query(BanditStats)
            .filter(
                BanditStats.assistant == assistant,
                BanditStats.category == category,
                BanditStats.recipe_id == recipe_id,
            )
            .first()
        )
        if row is None:
            row = BanditStats(
                assistant=assistant,
                category=category,
                recipe_id=recipe_id,
                sample_count=0,
                reward_sum=0.0,
                explore_count=0,
                exploit_count=0,
                first_seen_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(row)
        return row

    def increment_selection(self, db: Session, assistant: str, category: str, recipe_id: str, explored: bool) -> None:
        row = self._get_or_create(db, assistant, category, recipe_id)
        if explored:
            row.explore_count = int(row.explore_count or 0) + 1
        else:
            row.exploit_count = int(row.exploit_count or 0) + 1
        row.updated_at = datetime.utcnow()

    def upsert_feedback(self, db: Session, assistant: str, category: str, recipe_id: str, reward: float) -> None:
        row = self._get_or_create(db, assistant, category, recipe_id)
        row.sample_count = int(row.sample_count or 0) + 1
        row.reward_sum = float(row.reward_sum or 0.0) + float(reward)
        row.updated_at = datetime.utcnow()


def _average_for(recipe_id: str, stats: Dict[str, Dict[str, float]], optimistic: float) -> float:
    s = stats.get(recipe_id)
    if not s:
        return float(optimistic)
    cnt = float(s.get("sample_count", 0.0))
    if cnt <= 0:
        return float(optimistic)
    return float(s.get("reward_sum", 0.0)) / cnt


def epsilon_greedy_select(
    candidates: List[RecipeModel],
    stats: Dict[str, Dict[str, float]],
    epsilon: float,
    config: BanditConfig,
    rng: Optional[random.Random] = None,
) -> Tuple[RecipeModel, float, str, bool]:
    """Return (recipe, propensity, policy, explored_flag)."""
    if not candidates:
        raise ValueError("No candidate recipes available")
    rng = rng or random

    # Cold start
    under = [r for r in candidates if float(stats.get(r.id, {}).get("sample_count", 0.0)) < config.min_initial_samples]
    if under:
        choice = rng.choice(under)
        return choice, 1.0, "coldstart", True

    # Exploration
    if rng.random() < float(epsilon):
        choice = rng.choice(candidates)
        return choice, float(epsilon), "explore", True

    # Exploitation with random tie-break
    best_score = None
    best: List[RecipeModel] = []
    for r in candidates:
        score = _average_for(r.id, stats, config.optimistic_initial_value)
        if best_score is None or score > best_score + 1e-12:
            best_score = score
            best = [r]
        elif abs(score - (best_score or 0.0)) <= 1e-12:
            best.append(r)
    choice = rng.choice(best) if best else rng.choice(candidates)
    return choice, float(1.0 - float(epsilon)), "exploit", False


class BanditService:
    def __init__(self, config: BanditConfig, cache_ttl_seconds: int = 5):
        self.config = config
        self.repo = BanditStatsRepository()
        self._stats_cache: dict[tuple[str, str], tuple[Dict[str, Dict[str, float]], float]] = {}
        self._cache_ttl = float(cache_ttl_seconds)

    def select_recipe(
        self,
        db: Session,
        assistant: str,
        category: str,
        candidates: List[RecipeModel],
        epsilon: float,
    ) -> Tuple[RecipeModel, float, str, bool]:
        eligible = _eligible(candidates, db)
        if not eligible:
            eligible = candidates
        # Stats with small TTL cache
        key = (assistant, category)
        now = time.monotonic()
        cached = self._stats_cache.get(key)
        if cached and cached[1] > now:
            stats = cached[0]
        else:
            stats = self.repo.get_group_stats(db, assistant, category)
            self._stats_cache[key] = (stats, now + self._cache_ttl)
        t0 = time.monotonic()
        recipe, propensity, policy, explored = epsilon_greedy_select(
            eligible, stats, epsilon, self.config
        )
        metrics.BANDIT_SELECTION_LATENCY.observe(time.monotonic() - t0)
        # Count selection
        self.repo.increment_selection(db, assistant, category, recipe.id, explored)
        try:
            logger.info(
                "bandit.select",
                extra={
                    "assistant": assistant,
                    "category": category,
                    "recipe_id": recipe.id,
                    "policy": policy,
                    "explored": explored,
                    "epsilon": float(epsilon),
                },
            )
            metrics.BANDIT_SELECTED_TOTAL.labels(
                assistant=assistant,
                category=category,
                recipe_id=recipe.id,
                policy=str(policy),
                explored=str(bool(explored)).lower(),
            ).inc()
        except Exception:
            pass
        return recipe, propensity, policy, explored

    def record_feedback(self, db: Session, assistant: str, category: str, recipe_id: str, reward: float) -> None:
        t0 = time.monotonic()
        self.repo.upsert_feedback(db, assistant, category, recipe_id, reward)
        # Invalidate cache for this group
        self._stats_cache.pop((assistant, category), None)
        metrics.BANDIT_FEEDBACK_LATENCY.observe(time.monotonic() - t0)
        try:
            logger.info(
                "bandit.feedback",
                extra={
                    "assistant": assistant,
                    "category": category,
                    "recipe_id": recipe_id,
                    "reward": float(reward),
                },
            )
            metrics.BANDIT_FEEDBACK_TOTAL.labels(assistant=assistant, category=category, recipe_id=recipe_id).inc()
            metrics.BANDIT_REWARD_SUM.labels(assistant=assistant, category=category, recipe_id=recipe_id).inc(float(reward))
            metrics.BANDIT_REWARD_COUNT.labels(assistant=assistant, category=category, recipe_id=recipe_id).inc()
        except Exception:
            pass
