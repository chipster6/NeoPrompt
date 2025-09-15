import random
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.bandit import BanditService, BanditConfig
from backend.app.db import Base, BanditStats
from backend.app.recipes import RecipeModel


def mk_recipe(rid: str, assistant: str = "chatgpt", category: str = "coding") -> RecipeModel:
    return RecipeModel(id=rid, assistant=assistant, category=category, operators=["noop"], hparams={})


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_service_select_coldstart_marks_explored_and_counts():
    db = make_session()
    svc = BanditService(BanditConfig(min_initial_samples=1, optimistic_initial_value=0.0))
    candidates: List[RecipeModel] = [mk_recipe("r1"), mk_recipe("r2")]

    recipe, propensity, policy, explored = svc.select_recipe(db, "chatgpt", "coding", candidates, epsilon=0.0)
    assert policy == "coldstart"
    assert explored is True
    # Persist and check counters
    db.flush()
    row = db.query(BanditStats).filter(BanditStats.assistant == "chatgpt", BanditStats.category == "coding", BanditStats.recipe_id == recipe.id).first()
    assert row is not None
    assert int(row.explore_count or 0) == 1


def test_service_record_feedback_updates_stats():
    db = make_session()
    svc = BanditService(BanditConfig())
    svc.record_feedback(db, "chatgpt", "coding", "r1", 1.0)
    db.flush()
    row = db.query(BanditStats).filter(BanditStats.assistant == "chatgpt", BanditStats.category == "coding", BanditStats.recipe_id == "r1").first()
    assert row is not None
    assert int(row.sample_count or 0) == 1
    assert float(row.reward_sum or 0.0) == 1.0


def test_service_exploit_after_initial_samples():
    db = make_session()
    svc = BanditService(BanditConfig(min_initial_samples=0, optimistic_initial_value=0.0))
    candidates: List[RecipeModel] = [mk_recipe("best"), mk_recipe("worse")]

    # Seed feedback: best mean 0.8, worse mean 0.3
    for _ in range(8):
        svc.record_feedback(db, "chatgpt", "coding", "best", 1.0)
    for _ in range(2):
        svc.record_feedback(db, "chatgpt", "coding", "best", 0.0)
    for _ in range(3):
        svc.record_feedback(db, "chatgpt", "coding", "worse", 1.0)
    for _ in range(7):
        svc.record_feedback(db, "chatgpt", "coding", "worse", 0.0)
    db.flush()

    recipe, propensity, policy, explored = svc.select_recipe(db, "chatgpt", "coding", candidates, epsilon=0.0)
    assert policy == "exploit"
    assert explored is False
    assert recipe.id == "best"
    db.flush()
    row = db.query(BanditStats).filter(BanditStats.assistant == "chatgpt", BanditStats.category == "coding", BanditStats.recipe_id == "best").first()
    assert row is not None
    assert int(row.exploit_count or 0) >= 1