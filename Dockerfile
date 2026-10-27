# syntax=docker/dockerfile:1
# uv 0.13.0 wrote uv.lock (revision 5); keep the build tool in step with it.
FROM ghcr.io/astral-sh/uv:0.13.0 AS uv

FROM python:3.12.14-slim-trixie AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
# The image cannot be built from a bundle whose math fails the offline check (R1).
COPY content/compiled ./content/compiled
RUN /app/.venv/bin/python -m mathtutor.verify.content_check /src/content/compiled/problems.json

FROM python:3.12.14-slim-trixie
RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY content/compiled/ /app/content/compiled/
# Textbook corpus for help retrieval (chunks.jsonl + manifest.json, verified at load).
COPY content/corpus/ /app/content/corpus/
# Migrations run as a one-shot `alembic upgrade head` (compose service `migrate`) before the app.
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/
# SQLite lives on a volume mounted at /data, owned by the app user.
RUN mkdir /data && chown 10001:10001 /data
ARG GIT_SHA=dev
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MATHTUTOR_ENV=production \
    MATHTUTOR_CONTENT_PATH=/app/content/compiled/problems.json \
    MATHTUTOR_CORPUS_PATH=/app/content/corpus/chunks.jsonl \
    MATHTUTOR_DATABASE_URL=sqlite:////data/mathtutor.db \
    MATHTUTOR_GIT_SHA=$GIT_SHA
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]
# --forwarded-allow-ips '*' is safe only because port 8000 is never published:
# Caddy is the sole client, over the compose network. --no-access-log: the app writes its
# own request log (RequestLogMiddleware); uvicorn's would log every request twice.
CMD ["uvicorn", "mathtutor.web.app:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
