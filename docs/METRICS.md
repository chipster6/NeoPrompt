# Metrics

NeoPrompt exposes Prometheus metrics to track engine health, recipe reloads, and provider behavior. Scrape `/metrics` from the backend container or local FastAPI instance to ingest the data into Prometheus.

## Metric to use-case map

| Metric name | Type | Primary use-case |
|-------------|------|------------------|
| `neopr_recipes_reload_total{outcome,reason}` | Counter | Alert when filesystem reloads fail (e.g. bad YAML) or when hot-reload falls back to polling |
| `neopr_recipes_reload_duration_seconds_bucket` | Histogram | Track recipe reload latency spikes when the templates directory grows |
| `neopr_recipes_valid_count` | Gauge | Ensure CI keeps a full set of validated recipes before deployments |
| `neopr_bandit_selected_total{assistant,category,policy}` | Counter | Validate exploration vs. exploitation across assistants during optimize (M5) |
| `neopr_bandit_selection_latency_seconds_bucket` | Histogram | Watch decision latency when stress testing the optimizer |
| `neopr_bandit_epsilon` | Gauge | Confirm CI jobs pin epsilon to deterministic values |
| `neopr_hf_backoffs_total` | Counter | Monitor Hugging Face 429 retries to catch cold starts early in CI |
| `neopr_engine_latency_seconds_bucket` | Histogram | Measure `/engine/transform` p95 latency to enforce SLOs |

> The `neopr_hf_backoffs_total` and `neopr_engine_latency_seconds_bucket` families are exported by the HF adapter and engine middleware respectively. They complement the base counters defined in `backend/app/metrics.py`.

## Grafana quick start

Import the JSON snippet below into Grafana (Dashboards → New → Import) to get a starter view. Adjust the Prometheus datasource name as needed.

```json
{
  "annotations": {"list": []},
  "panels": [
    {
      "type": "stat",
      "title": "Recipe Errors",
      "targets": [{"expr": "sum(neopr_recipes_error_count)"}]
    },
    {
      "type": "timeseries",
      "title": "Engine p95 Latency",
      "fieldConfig": {"defaults": {"unit": "ms"}},
      "targets": [{"expr": "histogram_quantile(0.95, sum(rate(neopr_engine_latency_seconds_bucket[5m])) by (le))"}]
    },
    {
      "type": "timeseries",
      "title": "HF Backoffs",
      "targets": [{"expr": "sum(rate(neopr_hf_backoffs_total[5m]))"}]
    }
  ],
  "schemaVersion": 39,
  "title": "NeoPrompt Overview",
  "uid": "neoprompt-overview",
  "version": 1
}
```

This template surfaces recipe health, Hugging Face stability, and latency SLOs in a single dashboard so new contributors can reason about production readiness quickly.
