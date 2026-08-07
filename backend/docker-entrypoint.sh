#!/usr/bin/env sh
# Runs pending Alembic migrations before starting whatever CMD the image was
# given (Band 13: Deployment/DevOps — release process).
#
# Caveat, documented here and in docs/deployment.md: this is correct for a
# single-instance deployment (this repo's docker-compose setup). If this
# image is ever scaled to multiple replicas, running `alembic upgrade head`
# from every container's startup risks concurrent migration runs racing
# each other — move the migration step to a separate one-off release job
# instead, and drop it from this script.
set -e

echo "docker-entrypoint: running database migrations..."
alembic upgrade head

echo "docker-entrypoint: starting: $*"
exec "$@"
