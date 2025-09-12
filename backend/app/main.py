"""FastAPI app exposing routes for choose, feedback, history, recipes."""
from __future__ import annotations
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .schemas import (
    ChooseRequest,
    ChooseResponse,
    FeedbackRequest,
    FeedbackResponse,
    HistoryItem,
    HistoryResponse,
    RecipesResponse,
    Recipe as RecipeSchema,
)
from .db import get_db, init_db, Decision, Feedback
from .recipes import load_recipes, RecipeModel, validate_recipe
from .optimizer import select_recipe
from .engine import build_prompt
from .enhancer import Enhancer
from .guardrails import apply_domain_caps

RECIPES_DIR = os.getenv("RECIPES_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../recipes")))
STORE_TEXT = os.getenv("STORE_TEXT", "0") == "1"
ENHANCER_ENABLED = os.getenv("ENHANCER_ENABLED", "0") == "1"

app = FastAPI(title="Prompt Console API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def on_startup():
    init_db()


# Cache recipes in-memory; simple approach with reload query param to refresh
def _load_recipe_cache() -> tuple[list[RecipeModel], list[tuple[str, str]]]:
    recipes, errors = load_recipes(RECIPES_DIR)
    return recipes, errors


@app.post("/choose", response_model=ChooseResponse)
def choose(req: ChooseRequest, db: Session = Depends(get_db)):
    recipes, errors = _load_recipe_cache()
    candidates = [r for r in recipes if r.assistant == req.assistant and r.category == req.category]
    if not candidates:
        raise ValueError("No recipes available for the given assistant/category")

    # Optional enhancer
    raw = req.raw_input
    notes: list[str] = []
    if ENHANCER_ENABLED and req.options.get("enhance"):
        enh = Enhancer()
        enhanced = enh.enhance(raw, req.assistant, req.category)
        raw = enhanced
        notes.append("enhanced=true")
    else:
        notes.append("enhanced=false")

    # Selection via optimizer
    recipe, propensity, policy = select_recipe(db, req.assistant, req.category, candidates, epsilon=0.10)
    notes.append(f"policy={policy}")

    # Build prompt
    force_json = bool(req.options.get("force_json", False))
    prompt, applied_ops = build_prompt(
        raw_input=raw,
        category=req.category,
        operators=recipe.operators,
        force_json=force_json,
        examples=recipe.examples,
    )

    # Apply domain caps
    hparams = apply_domain_caps(req.category, recipe.hparams)

    # Persist decision
    decision_id = str(uuid.uuid4())
    dec = Decision(
        id=decision_id,
        assistant=req.assistant,
        category=req.category,
        recipe_id=recipe.id,
        propensity=propensity,
    )
    dec.set_context_dict({
        "input_tokens": req.context_features.get("input_tokens", 0),
        "lang": req.context_features.get("lang", "en"),
        "force_json": force_json,
        "enhanced": "enhanced=true" in notes,
    })
    dec.set_hparams_dict(hparams)
    dec.set_operators_list(applied_ops)
    if STORE_TEXT:
        dec.raw_input = req.raw_input
        dec.engineered_prompt = prompt
    db.add(dec)
    db.commit()

    return ChooseResponse(
        decision_id=decision_id,
        recipe_id=recipe.id,
        engineered_prompt=prompt,
        operators=applied_ops,
        hparams=hparams,
        propensity=propensity,
        notes=notes,
    )


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    fb = Feedback(
        decision_id=req.decision_id,
        reward=float(req.reward),
    )
    fb.set_components_dict({k: float(v) for k, v in req.reward_components.items()})
    fb.set_safety_flags_list(list(req.safety_flags))
    db.add(fb)
    db.commit()
    return FeedbackResponse(ok=True)


@app.get("/history", response_model=HistoryResponse)
def history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    assistant: Optional[str] = None,
    category: Optional[str] = None,
    with_text: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Decision)
    if assistant:
        q = q.filter(Decision.assistant == assistant)
    if category:
        q = q.filter(Decision.category == category)
    total = q.count()
    rows = q.order_by(Decision.ts.desc()).limit(limit).offset(offset).all()

    items: list[HistoryItem] = []
    for d in rows:
        items.append(
            HistoryItem(
                id=d.id,
                timestamp=d.ts,
                assistant=d.assistant,
                category=d.category,
                recipe_id=d.recipe_id,
                propensity=d.propensity,
                reward=d.feedback_record.reward if d.feedback_record else None,
                operators=d.get_operators_list(),
                raw_input=d.raw_input if with_text else None,
                engineered_prompt=d.engineered_prompt if with_text else None,
            )
        )

    return HistoryResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/recipes", response_model=RecipesResponse)
def recipes(reload: bool = False):
    recipes, errors = _load_recipe_cache()
    # Convert to API schema and include validation issues
    api_recipes: list[RecipeSchema] = []
    for r in recipes:
        api_recipes.append(
            RecipeSchema(
                id=r.id,
                assistant=r.assistant,
                category=r.category,
                operators=r.operators,
                hparams=r.hparams,
                guards=r.guards,
                examples=r.examples,
            )
        )
    error_objs = []
    for path, err in errors:
        error_objs.append({"file_path": path, "error": err, "line_number": None})
    return {"recipes": api_recipes, "errors": error_objs}

