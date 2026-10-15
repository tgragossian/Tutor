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

FROM python:3.12.14-slim-trixie
RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY content/compiled/ /app/content/compiled/
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MATHTUTOR_ENV=production \
    MATHTUTOR_CONTENT_PATH=/app/content/compiled/problems.json
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]
# --forwarded-allow-ips '*' is safe only because port 8000 is never published:
# Caddy is the sole client, over the compose network.
CMD ["uvicorn", "mathtutor.web.app:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
