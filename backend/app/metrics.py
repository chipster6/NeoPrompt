"""Prometheus metrics for bandit optimizer and hot-reload engine."""
from __future__ import annotations
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Selection metrics
BANDIT_SELECTED_TOTAL = Counter(
    "neopr_bandit_selected_total",
    "Selections made by the bandit",
    ["assistant", "category", "recipe_id", "policy", "explored"],
)

BANDIT_FEEDBACK_TOTAL = Counter(
    "neopr_bandit_feedback_total",
    "Feedback events recorded",
    ["assistant", "category", "recipe_id"],
)

BANDIT_REWARD_SUM = Counter(
    "neopr_bandit_reward_sum",
    "Cumulative reward sum",
    ["assistant", "category", "recipe_id"],
)

BANDIT_REWARD_COUNT = Counter(
    "neopr_bandit_reward_count",
    "Cumulative reward count",
    ["assistant", "category", "recipe_id"],
)

BANDIT_EPSILON = Gauge(
    "neopr_bandit_epsilon",
    "Current epsilon (exploration rate)",
)

BANDIT_SELECTION_LATENCY = Histogram(
    "neopr_bandit_selection_latency_seconds",
    "Time to select a recipe",
)

BANDIT_FEEDBACK_LATENCY = Histogram(
    "neopr_bandit_feedback_latency_seconds",
    "Time to record feedback",
)

# Hot-reload engine metrics
RECIPES_RELOAD_TOTAL = Counter(
    "neopr_recipes_reload_total",
    "Total recipe reload attempts",
    ["outcome", "reason"],
)

RECIPES_RELOAD_DURATION = Histogram(
    "neopr_recipes_reload_duration_seconds",
    "Duration of recipe reloads",
)

RECIPES_VALID_COUNT = Gauge(
    "neopr_recipes_valid_count",
    "Current count of valid recipes",
)

RECIPES_ERROR_COUNT = Gauge(
    "neopr_recipes_error_count",
    "Current count of recipe validation errors",
)

# -----------------------------
# Engine API metrics (M1)
# -----------------------------
from prometheus_client import Counter as _Counter, Histogram as _Histogram

neopr_engine_requests_total = _Counter(
    "neopr_engine_requests_total",
    "Total Engine API requests",
    labelnames=("endpoint",),
)

neopr_engine_latency_seconds = _Histogram(
    "neopr_engine_latency_seconds",
    "Engine API latency in seconds",
    labelnames=("endpoint",),
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)

# -----------------------------
# HF provider metrics (M1)
# -----------------------------
neopr_hf_backoffs_total = _Counter(
    "neopr_hf_backoffs_total",
    "Total number of HF backoff events",
)

neopr_hf_rate_limited_total = _Counter(
    "neopr_hf_rate_limited_total",
    "Total number of HF 429 rate limited responses",
)

# Pre-register metrics so names appear even if zero
neopr_hf_backoffs_total.inc(0)
neopr_hf_rate_limited_total.inc(0)

# Pre-create labelled samples for engine endpoints so they appear in metrics output
for _endpoint in ("plan", "score", "transform"):
    neopr_engine_requests_total.labels(endpoint=_endpoint).inc(0)
    neopr_engine_latency_seconds.labels(endpoint=_endpoint)

def set_epsilon_gauge(epsilon: float) -> None:
    try:
        BANDIT_EPSILON.set(float(epsilon))
    except Exception:
        pass


def metrics_response() -> tuple[bytes, str]:
    data = generate_latest()
    return data, CONTENT_TYPE_LATEST
