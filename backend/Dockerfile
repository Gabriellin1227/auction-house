FROM ghcr.io/astral-sh/uv:0.13.6 AS uv
FROM python:3.12.12-slim-bookworm AS runtime
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app \
    && mkdir -p /data/media /data/audit && chown -R app:app /data
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test
USER root
RUN uv sync --locked --no-install-project
COPY tests ./tests
USER app
ENV PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest_cache"
CMD ["pytest", "-c", "pyproject.toml"]
