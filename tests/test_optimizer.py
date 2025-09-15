import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import Base, Decision, Feedback
from backend.app.optimizer import select_recipe, get_optimizer_stats
from backend.app.recipes import RecipeModel


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def seed_data(db):
    d1 = Decision(id="d1", assistant="chatgpt", category="coding", recipe_id="r1", propensity=1.0)
    d1.set_context_dict({})
    d1.set_hparams_dict({})
    d1.set_operators_list(["role_hdr"])
    d2 = Decision(id="d2", assistant="chatgpt", category="coding", recipe_id="r2", propensity=1.0)
    d2.set_context_dict({})
    d2.set_hparams_dict({})
    d2.set_operators_list(["role_hdr"])
    db.add_all([d1, d2])
    db.commit()
    fb1 = Feedback(decision_id="d1", reward=0.2)
    fb1.set_components_dict({"user_like": 0.2})
    fb1.set_safety_flags_list([])
    fb2 = Feedback(decision_id="d2", reward=0.9)
    fb2.set_components_dict({"user_like": 0.9})
    fb2.set_safety_flags_list([])
    db.add_all([fb1, fb2])
    db.commit()


def test_select_recipe_exploit_vs_explore():
    db = make_session()
    seed_data(db)
    candidates = [
        RecipeModel(id="r1", assistant="chatgpt", category="coding", operators=["role_hdr"], hparams={}, guards={}, examples=[]),
        RecipeModel(id="r2", assistant="chatgpt", category="coding", operators=["role_hdr"], hparams={}, guards={}, examples=[]),
    ]
    # Epsilon=0 -> exploit best mean
    recipe, prop, policy = select_recipe(db, "chatgpt", "coding", candidates, epsilon=0.0)
    assert recipe.id == "r2"
    assert prop == 1.0
    assert policy == "exploit"

    # Epsilon=1 -> explore always (random choice)
    random.seed(0)
    recipe2, prop2, policy2 = select_recipe(db, "chatgpt", "coding", candidates, epsilon=1.0)
    assert recipe2.id in {"r1", "r2"}
    assert prop2 == 1.0
    assert policy2 == "explore"


def test_get_optimizer_stats():
    db = make_session()
    seed_data(db)
    rows = get_optimizer_stats(db, assistant="chatgpt", category="coding")
    # Expect two rows, r2 has higher mean than r1
    ids = {r["recipe_id"] for r in rows}
    assert {"r1", "r2"} == ids
    means = {r["recipe_id"]: r["mean_reward"] for r in rows}
    assert means["r2"] > means["r1"]