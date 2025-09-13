"""Epsilon-greedy recipe selector based on observed rewards.
Computes mean rewards per recipe using past decisions and feedback.
"""
from __future__ import annotations
import random
from typing import List, Tuple, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from .db import Decision, Feedback
from .recipes import RecipeModel


def _fetch_recipe_stats(db: Session, assistant: str, category: str) -> Dict[str, Dict[str, float]]:
    """Return stats per recipe_id: { mean_reward, count } for given assistant/category."""
    q = (
        db.query(Decision.recipe_id, func.avg(Feedback.reward), func.count(Feedback.reward))
        .join(Feedback, Feedback.decision_id == Decision.id)
        .filter(Decision.assistant == assistant, Decision.category == category)
        .group_by(Decision.recipe_id)
    )
    stats: Dict[str, Dict[str, float]] = {}
    for recipe_id, avg_reward, count in q.all():
        stats[recipe_id] = {"mean_reward": float(avg_reward or 0.0), "count": float(count or 0)}
    return stats


def get_optimizer_stats(
    db: Session,
    assistant: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Return list of stats rows across assistant/category/recipe.
    Each row: {assistant, category, recipe_id, mean_reward, count}
    Optionally filter by assistant/category.
    """
    q = (
        db.query(
            Decision.assistant,
            Decision.category,
            Decision.recipe_id,
            func.avg(Feedback.reward),
            func.count(Feedback.reward),
        )
        .join(Feedback, Feedback.decision_id == Decision.id)
        .group_by(Decision.assistant, Decision.category, Decision.recipe_id)
    )
    if assistant:
        q = q.filter(Decision.assistant == assistant)
    if category:
        q = q.filter(Decision.category == category)
    rows = []
    for a, c, rid, avg_reward, cnt in q.all():
        rows.append(
            {
                "assistant": a,
                "category": c,
                "recipe_id": rid,
                "mean_reward": float(avg_reward or 0.0),
                "count": int(cnt or 0),
            }
        )
    return rows


def _last_n_rewards(db: Session, recipe_id: str, n: int = 3) -> List[float]:
    q = (
        db.query(Feedback.reward)
        .join(Decision, Decision.id == Feedback.decision_id)
        .filter(Decision.recipe_id == recipe_id)
        .order_by(Feedback.ts.desc())
        .limit(n)
    )
    return [float(r[0]) for r in q.all()]


def _eligible(recipes: List[RecipeModel], db: Session, safety_threshold: float = 0.2) -> List[RecipeModel]:
    """Exclude recipes whose last 3 rewards are all below threshold."""
    eligible = []
    for r in recipes:
        last3 = _last_n_rewards(db, r.id, 3)
        if len(last3) == 3 and all(rv < safety_threshold for rv in last3):
            continue
        eligible.append(r)
    return eligible


def select_recipe(
    db: Session,
    assistant: str,
    category: str,
    candidates: List[RecipeModel],
    epsilon: float = 0.10,
) -> Tuple[RecipeModel, float, str]:
    """Select a recipe via epsilon-greedy. Returns (recipe, propensity, policy)."""
    if not candidates:
        raise ValueError("No candidate recipes available")

    original_candidates = list(candidates)
    candidates = _eligible(candidates, db)
    if not candidates:
        # Fall back to original if safety filter removed all
        candidates = original_candidates

    # Exploration
    if random.random() < epsilon:
        choice = random.choice(candidates)
        return choice, epsilon, "explore"

    # Exploitation: choose highest mean reward
    stats = _fetch_recipe_stats(db, assistant, category)
    best = None
    best_score = -1.0
    for r in candidates:
        score = stats.get(r.id, {}).get("mean_reward", 0.0)
        if score > best_score:
            best = r
            best_score = score
    if best is None:
        best = random.choice(candidates)
    propensity = 1.0 - epsilon
    return best, propensity, "exploit"
