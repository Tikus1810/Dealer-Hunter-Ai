FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build tools + Postgres client headers, needed only to compile wheels
# (argon2-cffi, some transitive C extensions) — none of this ships in the
# runtime stage below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# curl is used by the HEALTHCHECK below. asyncpg/psycopg2-binary bundle
# their own Postgres client library, so no libpq runtime package is needed
# here — that's most of the size win over a single-stage build.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN chmod +x docker-entrypoint.sh \
    && useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness only (GET /api/v1/health — no DB/Redis dependency). Readiness
# (GET /api/v1/ready) is deliberately not used here: an orchestrator's own
# readiness probe should own routing decisions during a DB blip, not
# Docker's HEALTHCHECK, which only gates `docker ps`/`depends_on: service_
# healthy` in docker-compose (see infra/docker/docker-compose.yml).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
