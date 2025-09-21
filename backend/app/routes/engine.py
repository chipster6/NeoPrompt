from __future__ import annotations
from typing import Any, Dict, List, Optional
from time import perf_counter

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.engine_ir.models.prompt_doc import PromptDoc
from backend.app.engine_ir.rulepacks.loader import resolve as resolve_rulepacks
from backend.app.engine_ir.operators import run_plan
from backend.app.metrics import neopr_engine_requests_total, neopr_engine_latency_seconds

router = APIRouter(prefix="/engine", tags=["engine"])


class PlanRequest(BaseModel):
    model: Optional[str] = None
    category: Optional[str] = None
    overrides: Dict[str, Any] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    packs_applied: List[str]
    directives: Dict[str, Any]
    operator_plan: List[str]


class ScoreRequest(BaseModel):
    prompt_doc: PromptDoc


class ScoreResponse(BaseModel):
    signals: Dict[str, Any]
    score: float


class TransformRequest(BaseModel):
    model: Optional[str] = None
    category: Optional[str] = None
    prompt_doc: PromptDoc


class TransformResponse(BaseModel):
    packs_applied: List[str]
    operator_plan: List[str]
    prompt_doc: PromptDoc
    hlep_text: str


@router.post("/plan", response_model=PlanResponse)
def engine_plan(req: PlanRequest) -> PlanResponse:
    start = perf_counter()
    try:
        res = resolve_rulepacks(req.model, req.category)
        return PlanResponse(
            packs_applied=res["packs_applied"],
            directives=res["directives"],
            operator_plan=res["operator_plan"],
        )
    finally:
        neopr_engine_requests_total.labels(endpoint="plan").inc()
        neopr_engine_latency_seconds.labels(endpoint="plan").observe(perf_counter() - start)


@router.post("/score", response_model=ScoreResponse)
def engine_score(req: ScoreRequest) -> ScoreResponse:
    start = perf_counter()
    try:
        pd = req.prompt_doc
        constraints = len(pd.sections.constraints or [])
        has_io = 1 if (pd.sections.io_format or "").strip() else 0
        has_examples = 1 if (pd.sections.examples or []) else 0
        score = min(1.0, 0.5 + 0.1 * constraints + 0.15 * has_io + 0.15 * has_examples)
        signals = {
            "constraints_count": constraints,
            "has_io_format": bool(has_io),
            "has_examples": bool(has_examples),
        }
        return ScoreResponse(signals=signals, score=round(score, 3))
    finally:
        neopr_engine_requests_total.labels(endpoint="score").inc()
        neopr_engine_latency_seconds.labels(endpoint="score").observe(perf_counter() - start)


@router.post("/transform", response_model=TransformResponse)
def engine_transform(req: TransformRequest) -> TransformResponse:
    start = perf_counter()
    try:
        res = resolve_rulepacks(req.model, req.category)
        plan = res["operator_plan"]
        pd = run_plan(req.prompt_doc, plan)
        hlep = pd.to_hlep()
        pd.packs_applied = res["packs_applied"]
        return TransformResponse(
            packs_applied=res["packs_applied"],
            operator_plan=plan,
            prompt_doc=pd,
            hlep_text=hlep,
        )
    finally:
        neopr_engine_requests_total.labels(endpoint="transform").inc()
        neopr_engine_latency_seconds.labels(endpoint="transform").observe(perf_counter() - start)
