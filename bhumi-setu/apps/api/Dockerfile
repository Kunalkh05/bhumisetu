# syntax=docker/dockerfile:1
#
# The api image. Also the image for `worker-general` and `worker-beat`, because
# every Celery process runs the one app declared in app/workers/celery_app.py —
# that is where §13.7's queues and task routes live, and a process booting a
# second Celery app would publish to one topology and consume from another.
#
# The image carries no application source: compose mounts ./apps/api at /app so a
# code change is picked up by --reload without a rebuild. Only the dependency
# layer is baked, which is what makes the mount cheap.

FROM python:3.11-slim

# PYTHONDONTWRITEBYTECODE keeps .pyc files out of the mounted source tree.
# PYTHONUNBUFFERED so log lines reach `docker compose logs` as they happen.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg[binary] ships its own libpq, so there is no build toolchain and no
# libpq-dev here. curl is present for the compose healthcheck against /healthz.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies in their own layer, pinned in requirements.txt.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Non-root. Nothing in the API writes to the filesystem: documents go to object
# storage (§13.1) and state goes to PostgreSQL.
RUN useradd --create-home --uid 10001 bhumisetu
USER bhumisetu

EXPOSE 8000

# Overridden by each compose service: uvicorn for api, `celery worker` for
# worker-general, `celery beat` for worker-beat.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
