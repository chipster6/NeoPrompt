"""FastAPI app exposing routes for choose, feedback, history, recipes."""
from __future__ import annotations
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, Query, HTTPException, Body
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
    StatsResponse,
    StatsItem,
)
from .db import get_db, init_db, Decision, Feedback
from .recipes import load_recipes, RecipeModel, validate_recipe
from .optimizer import select_recipe, get_optimizer_stats
from .engine import build_prompt
from .enhancer import Enhancer
from .guardrails import apply_domain_caps, sanitize_text

RECIPES_DIR = os.getenv("RECIPES_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../recipes")))
STORE_TEXT = os.getenv("STORE_TEXT", "0") == "1"
ENHANCER_ENABLED = os.getenv("ENHANCER_ENABLED", "0") == "1"
DEFAULT_EPSILON = float(os.getenv("EPSILON", "0.10"))

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
    app.state.epsilon = DEFAULT_EPSILON


# Cache recipes in-memory; simple approach with reload query param to refresh
def _load_recipe_cache() -> tuple[list[RecipeModel], list[tuple[str, str]]]:
    recipes, errors = load_recipes(RECIPES_DIR)
    return recipes, errors


@app.post("/choose", response_model=ChooseResponse)
def choose(req: ChooseRequest, db: Session = Depends(get_db)):
    recipes, errors = _load_recipe_cache()
    candidates = [r for r in recipes if r.assistant == req.assistant and r.category == req.category]

    # Fallback strategy: prefer a baseline recipe for the requested assistant,
    # then any recipe for that assistant, then a recipe for the requested category,
    # and finally any available recipe.
    pre_notes: list[str] = []
    if not candidates:
        assistant_recipes = [r for r in recipes if r.assistant == req.assistant]
        chosen = None
        if assistant_recipes:
            baseline = [r for r in assistant_recipes if r.id.endswith(".baseline")]
            chosen = baseline[0] if baseline else assistant_recipes[0]
            pre_notes.append("fallback=assistant")
        else:
            cat_recipes = [r for r in recipes if r.category == req.category]
            if cat_recipes:
                chosen = cat_recipes[0]
                pre_notes.append("fallback=category")
            elif recipes:
                chosen = recipes[0]
                pre_notes.append("fallback=any")
        if chosen:
            candidates = [chosen]
        else:
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
    # Include any pre-collected fallback notes
    notes.extend(pre_notes)
        else:
            notes.append("enhanced=false")

        # Sanitize input (guardrails)
        cleaned = sanitize_text(raw)
        if cleaned != raw:
            notes.append("sanitized=true")
            raw = cleaned
        else:
            notes.append("sanitized=false")

        # Selection via optimizer
        epsilon = float(getattr(app.state, "epsilon", DEFAULT_EPSILON))
        recipe, propensity, policy = select_recipe(db, req.assistant, req.category, candidates, epsilon=epsilon)
        notes.append(f"policy={policy}")
        notes.append(f"epsilon={epsilon:.2f}")

        # Build prompt
        force_json = bool(req.options.get("force_json", False))
        prompt, applied_ops = build_prompt(
            raw_input=raw,
            category=req.category,
            operators=recipe.operators,
            force_json=force_json,
            examples=recipe.examples,
        )

        # Apply domain caps and record if cap applied
        capped = apply_domain_caps(req.category, recipe.hparams)
        hparams = capped
        if float(recipe.hparams.get("temperature", 0.0)) != float(capped.get("temperature", 0.0)):
            notes.append("temperature_capped=true")

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
        # Decide whether to persist raw/engineered text
        per_request_store = bool(req.context_features.get("store_text", False))
        if STORE_TEXT or per_request_store:
            dec.raw_input = req.raw_input
            dec.engineered_prompt = prompt
            notes.append("store_text=true")
        else:
            notes.append("store_text=false")
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"choose_failed: {type(e).__name__}")


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        # Validate decision exists
        d = db.query(Decision).filter(Decision.id == req.decision_id).first()
        if d is None:
            raise HTTPException(status_code=404, detail="decision_not_found")
        fb = Feedback(
            decision_id=req.decision_id,
            reward=float(req.reward),
        )
        fb.set_components_dict({k: float(v) for k, v in req.reward_components.items()})
        fb.set_safety_flags_list(list(req.safety_flags))
        db.add(fb)
        db.commit()
        return FeedbackResponse(ok=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"feedback_failed: {type(e).__name__}")


@app.get("/history", response_model=HistoryResponse)
def history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    assistant: Optional[str] = None,
    category: Optional[str] = None,
    with_text: bool = False,
    db: Session = Depends(get_db),
):
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"history_failed: {type(e).__name__}")


@app.get("/recipes", response_model=RecipesResponse)
def recipes(reload: bool = False):
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"recipes_failed: {type(e).__name__}")


@app.get("/stats", response_model=StatsResponse)
def get_stats(
    assistant: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        items = [
            StatsItem(
                assistant=row["assistant"],
                category=row["category"],
                recipe_id=row["recipe_id"],
                mean_reward=row["mean_reward"],
                count=row["count"],
            )
            for row in get_optimizer_stats(db, assistant=assistant, category=category)
        ]
        epsilon = float(getattr(app.state, "epsilon", DEFAULT_EPSILON))
        return StatsResponse(epsilon=epsilon, items=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"stats_failed: {type(e).__name__}")


@app.post("/stats", response_model=StatsResponse)
def update_stats(
    epsilon: Optional[float] = Body(None, ge=0.0, le=1.0),
    reset: bool = Body(False),
    assistant: Optional[str] = Body(None),
    category: Optional[str] = Body(None),
    db: Session = Depends(get_db),
):
    """Update epsilon and/or reset optimizer stats (feedback). If assistant/category provided, reset only that subset."""
    try:
        if epsilon is not None:
            app.state.epsilon = float(epsilon)
        if reset:
            # Delete feedback rows (optionally filtered by assistant/category)
            if assistant or category:
                q = db.query(Feedback).join(Decision, Decision.id == Feedback.decision_id)
                if assistant:
                    q = q.filter(Decision.assistant == assistant)
                if category:
                    q = q.filter(Decision.category == category)
                deleted = 0
                for fb in q.all():
                    db.delete(fb)
                    deleted += 1
            else:
                db.query(Feedback).delete()
            db.commit()
        # Return fresh stats
        items = [
            StatsItem(
                assistant=row["assistant"],
                category=row["category"],
                recipe_id=row["recipe_id"],
                mean_reward=row["mean_reward"],
                count=row["count"],
            )
            for row in get_optimizer_stats(db, assistant=assistant, category=category)
        ]
        eps = float(getattr(app.state, "epsilon", DEFAULT_EPSILON))
        return StatsResponse(epsilon=eps, items=items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"stats_update_failed: {type(e).__name__}")

