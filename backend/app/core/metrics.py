"""Prometheus metrics (Band 13: Deployment/DevOps — Monitoring).

Hand-scoped to what a first production deployment actually needs to alert
on — request rate, error rate, latency — rather than an auto-instrumenting
kitchen sink nothing dashboards yet. `prometheus_client` (the reference
Python client) does the encoding; `app/main.py`'s middleware records into
these, and `GET /metrics` (also wired there) exposes them in the Prometheus
text exposition format for a scraper to pull. No scraper is deployed by
this repo (no cloud/monitoring account exists yet — see docs/deployment.md)
but the endpoint itself needs no external service to work or be verified.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests processed",
    ["method", "path_template", "status_code"],
)

REQUEST_LATENCY_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path_template"],
)
