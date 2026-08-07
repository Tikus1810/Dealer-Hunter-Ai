"""Unit tests for the OWASP secure-headers middleware (Band 14:
Security-Härtung, app.main.security_headers_middleware).
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_json_api_response_gets_the_full_header_set() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in response.headers["Permissions-Policy"]
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )


async def test_swagger_ui_is_exempt_from_the_content_security_policy() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/docs")

    # Still gets the headers that don't conflict with Swagger's own assets...
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    # ...but not a CSP that would block its inline scripts/CDN resources.
    assert "Content-Security-Policy" not in response.headers


async def test_openapi_json_is_not_exempt_from_the_content_security_policy() -> None:
    """Only the HTML docs pages need the exemption — the raw OpenAPI JSON
    document is just data, same as every other endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/openapi.json")

    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )


async def test_hsts_is_absent_outside_production() -> None:
    """The default test/dev settings run with APP_ENV=development (or
    unset) — Settings.is_production is False, so HSTS must not be sent
    (see the middleware's own comment on why sending it over non-TLS
    environments would be actively harmful)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert "Strict-Transport-Security" not in response.headers
