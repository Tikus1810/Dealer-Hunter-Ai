"""Unit test for the Prometheus metrics middleware + GET /metrics
(Band 13: Deployment/DevOps — Monitoring). Asserts on label *presence*,
not full-line equality or exact counts: `REQUEST_COUNT`/`REQUEST_LATENCY_
SECONDS` (app/core/metrics.py) are process-global registries every other
test hitting `app.main.app` also increments, and prometheus_client's label
ordering in the text exposition format is an implementation detail this
test shouldn't pin down.
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_metrics_endpoint_records_a_completed_request() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/health")
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    body = response.text
    health_count_lines = [
        line
        for line in body.splitlines()
        if line.startswith("http_requests_total{") and "/api/v1/health" in line
    ]
    assert health_count_lines, "expected a http_requests_total series for /api/v1/health"
    line = health_count_lines[0]
    assert 'method="GET"' in line
    assert 'path_template="/api/v1/health"' in line
    assert 'status_code="200"' in line

    assert any(
        line.startswith("http_request_duration_seconds") and "/api/v1/health" in line
        for line in body.splitlines()
    )
