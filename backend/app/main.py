"""FastAPI app exposing routes for choose, feedback, history, recipes."""
from __future__ import annotations
import os
import uuid
import logging
import asyncio
import random
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
from .recipes import load_recipes, RecipeModel, validate_recipe, RecipesCache, RecipeError, filter_recipes
from .optimizer import select_recipe, get_optimizer_stats
from .bandit import BanditService, BanditConfig
from . import metrics
from .bandit import BanditService, BanditConfig
from .enhancer import Enhancer
from .guardrails import apply_domain_caps, sanitize_text

RECIPES_DIR = os.getenv("RECIPES_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../recipes")))
STORE_TEXT = os.getenv("STORE_TEXT", "0") == "1"
ENHANCER_ENABLED = os.getenv("ENHANCER_ENABLED", "0") == "1"
DEFAULT_EPSILON = float(os.getenv("EPSILON", "0.10"))
BANDIT_ENABLED = os.getenv("BANDIT_ENABLED", "1") == "1"
BANDIT_MIN_INITIAL_SAMPLES = int(os.getenv("BANDIT_MIN_INITIAL_SAMPLES", "1"))
BANDIT_OPTIMISTIC_INITIAL_VALUE = float(os.getenv("BANDIT_OPTIMISTIC_INITIAL_VALUE", "0.0"))
RECIPES_RELOAD_INTERVAL_SECONDS = float(os.getenv("RECIPES_RELOAD_INTERVAL_SECONDS", "5"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("prompt_console")

from prometheus_client import make_asgi_app

app = FastAPI(title="Prompt Console API", version="0.1.0")
# Mount /metrics for Prometheus (optional; lightweight)
app.mount("/metrics", make_asgi_app())
app.state.recipes_cache = RecipesCache(RECIPES_DIR)
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
    metrics.set_epsilon_gauge(app.state.epsilon)
    try:
        logger.info("Startup complete. RECIPES_DIR=%s EPSILON=%.2f", RECIPES_DIR, app.state.epsilon)
    except Exception:
        pass
    # Initialize bandit service with defaults; guard if bandit module unavailable
    try:
        app.state.bandit_service = BanditService(BanditConfig(min_initial_samples=BANDIT_MIN_INITIAL_SAMPLES, optimistic_initial_value=BANDIT_OPTIMISTIC_INITIAL_VALUE))
    except Exception:
        # Leave unset; choose() will treat as disabled if missing
        pass

    # Start background polling task for recipes hot-reload
    async def _recipes_reloader():
        cache = app.state.recipes_cache
        interval = max(0.5, float(RECIPES_RELOAD_INTERVAL_SECONDS))
        while True:
            try:
                # small jitter to avoid lockstep with editors
                jitter = random.uniform(-0.3, 0.3) * interval
                await asyncio.sleep(max(0.1, interval + jitter))
                cache.ensure_loaded(force=True)
            except asyncio.CancelledError:
                break
            except Exception:
                # Keep loop alive; errors surface via /recipes
                pass

    app.state.recipes_reload_task = asyncio.create_task(_recipes_reloader())


# Recipes cache: serve last-known-good; allow force reload via flag
def _load_recipe_cache(force: bool = False) -> tuple[list[RecipeModel], list[RecipeError]]:
    cache = getattr(app.state, "recipes_cache")
    recipes, errors = cache.ensure_loaded(force=force)
    return recipes, errors


@app.post("/choose", response_model=ChooseResponse)
def choose(req: ChooseRequest, db: Session = Depends(get_db)):
    try:
        recipes, errors = _load_recipe_cache(force=False)
        # Tiered candidate filtering
        candidates, tier, tier_notes = filter_recipes(recipes, req.assistant, req.category)
        if not candidates:
            # If no candidates at all, treat as service unavailable (invalid library)
            raise HTTPException(status_code=503, detail={"code": "recipes_unavailable", "message": "No valid recipes available, see /recipes for details"})
        pre_notes: list[str] = tier_notes

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

        # Sanitize input (guardrails)
        cleaned = sanitize_text(raw)
        if cleaned != raw:
            notes.append("sanitized=true")
            raw = cleaned
        else:
            notes.append("sanitized=false")

        # Selection via optimizer (feature-flagged)
        policy = "disabled" if not BANDIT_ENABLED else None
        epsilon = float(getattr(app.state, "epsilon", DEFAULT_EPSILON))
        if BANDIT_ENABLED and hasattr(app.state, "bandit_service"):
            bs: BanditService = app.state.bandit_service
            recipe, propensity, policy, explored = bs.select_recipe(db, req.assistant, req.category, candidates, epsilon=epsilon)
        else:
            # Deterministic fallback to first candidate
            recipe = candidates[0]
            propensity = 1.0
            explored = False
        notes.append(f"policy={policy}")
        notes.append(f"epsilon={epsilon:.2f}")
        notes.append(f"explored={str(explored).lower()}")

        # Build prompt
        from .engine import build_prompt  # local import to avoid test import cycles
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
            "language": req.context_features.get("language", req.context_features.get("lang", "en")),
            "force_json": force_json,
            "enhanced": "enhanced=true" in notes,
            "policy": policy,
            "epsilon": epsilon,
            "explored": explored,
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
        logger.exception("choose_failed: %s", e)
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
        # Update bandit persistent stats if available
        if hasattr(app.state, "bandit_service"):
            bs: BanditService = app.state.bandit_service
            bs.record_feedback(db, d.assistant, d.category, d.recipe_id, float(req.reward))
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
        recipes, errors = _load_recipe_cache(force=bool(reload))
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
        for err in errors:
            severity = "warning" if getattr(err, "error_type", None) == "semantic_validation" else "error"
            error_objs.append({
                "file_path": err.file_path,
                "error": err.error,
                "line_number": err.line_number,
                "error_type": getattr(err, "error_type", None),
                "severity": severity,
            })
            
        return {"recipes": api_recipes, "errors": error_objs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"recipes_failed: {type(e).__name__}")


@app.get("/bandit_stats")
def get_bandit_stats(assistant: Optional[str] = None, category: Optional[str] = None, db: Session = Depends(get_db)):
    # Return current BanditStats snapshot with avg_reward
    q = db.query(
        Decision.assistant,
        Decision.category,
        Decision.recipe_id,
    )
    # We will pull BanditStats directly to avoid expensive joins
    from .db import BanditStats as _BS
    bsq = db.query(_BS).filter(True)
    if assistant:
        bsq = bsq.filter(_BS.assistant == assistant)
    if category:
        bsq = bsq.filter(_BS.category == category)
    rows = []
    for r in bsq.all():
        cnt = int(r.sample_count or 0)
        s = float(r.reward_sum or 0.0)
        avg = (s / cnt) if cnt > 0 else 0.0
        rows.append({
            "assistant": r.assistant,
            "category": r.category,
            "recipe_id": r.recipe_id,
            "sample_count": cnt,
            "reward_sum": s,
            "avg_reward": avg,
            "explore_count": int(r.explore_count or 0),
            "exploit_count": int(r.exploit_count or 0),
            "updated_at": r.updated_at,
        })
    return {"items": rows, "epsilon": float(getattr(app.state, "epsilon", DEFAULT_EPSILON))}


@app.post("/bandit_config")
def set_bandit_config(
    epsilon: Optional[float] = Body(None, ge=0.0, le=1.0),
    min_initial_samples: Optional[int] = Body(None, ge=0),
    optimistic_initial_value: Optional[float] = Body(None, ge=0.0, le=1.0),
):
    # Update global bandit parameters
    if epsilon is not None:
        app.state.epsilon = float(epsilon)
        metrics.set_epsilon_gauge(app.state.epsilon)
    if hasattr(app.state, "bandit_service"):
        bs: BanditService = app.state.bandit_service
        if min_initial_samples is not None:
            bs.config.min_initial_samples = int(min_initial_samples)
        if optimistic_initial_value is not None:
            bs.config.optimistic_initial_value = float(optimistic_initial_value)
    return {"epsilon": float(getattr(app.state, "epsilon", DEFAULT_EPSILON)), "config": {
        "min_initial_samples": getattr(app.state.bandit_service.config, "min_initial_samples", None) if hasattr(app.state, "bandit_service") else None,
        "optimistic_initial_value": getattr(app.state.bandit_service.config, "optimistic_initial_value", None) if hasattr(app.state, "bandit_service") else None,
    }}


@app.post("/bandit_backfill")
def bandit_backfill(assistant: Optional[str] = Body(None), category: Optional[str] = Body(None), db: Session = Depends(get_db)):
    # Aggregate Decision+Feedback and seed BanditStats
    from sqlalchemy import func
    from .db import BanditStats as _BS
    q = (
        db.query(
            Decision.assistant,
            Decision.category,
            Decision.recipe_id,
            func.count(Feedback.reward),
            func.sum(Feedback.reward),
        )
        .join(Feedback, Feedback.decision_id == Decision.id)
        .group_by(Decision.assistant, Decision.category, Decision.recipe_id)
    )
    if assistant:
        q = q.filter(Decision.assistant == assistant)
    if category:
        q = q.filter(Decision.category == category)
    inserted = 0
    for a, c, rid, cnt, s in q.all():
        row = db.query(_BS).filter(_BS.assistant == a, _BS.category == c, _BS.recipe_id == rid).first()
        if row is None:
            row = _BS(assistant=a, category=c, recipe_id=rid, sample_count=int(cnt or 0), reward_sum=float(s or 0.0))
            db.add(row)
        else:
            row.sample_count = int(cnt or 0)
            row.reward_sum = float(s or 0.0)
        inserted += 1
    db.commit()
    return {"ok": True, "rows": inserted}


@app.get("/metrics")
def metrics_endpoint():
    data, content_type = metrics.metrics_response()
    from fastapi import Response
    return Response(content=data, media_type=content_type)


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
            metrics.set_epsilon_gauge(app.state.epsilon)
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


@app.on_event("shutdown")
async def on_shutdown():
    # Cancel background reloader task if running
    task = getattr(app.state, "recipes_reload_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except Exception:
            pass

