"""Integration test for GET /api/v1/ready against real Postgres/Redis (the
CI services — see .github/workflows/ci.yml) — verifies the checks in
app.main.ready() actually work against real connections, not just the
monkeypatched fakes in tests/unit/test_readiness.py.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.integration


async def test_ready_endpoint_returns_200_against_real_dependencies() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "ok"}
