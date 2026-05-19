# syntax=docker/dockerfile:1.7

# --- Stage 1: build dashboard ---
FROM node:22-alpine AS dashboard-build
WORKDIR /app/dashboard
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm ci
COPY dashboard ./
RUN npm run build

# --- Stage 2: server runtime ---
FROM python:3.12-slim AS server
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/server
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# Install deps first (layer-cache).
COPY server/pyproject.toml server/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then copy source.
COPY server ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Dashboard bundle from stage 1.
COPY --from=dashboard-build /app/dashboard/dist /app/dashboard/dist

ENV KNCT_HOST=0.0.0.0 \
    KNCT_PORT=8765 \
    KNCT_DASHBOARD_DIST=/app/dashboard/dist \
    KNCT_DATABASE_URL=sqlite+aiosqlite:////data/hub.db \
    PATH="/app/server/.venv/bin:$PATH"

EXPOSE 8765
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/api/v1/health').read()" || exit 1

CMD ["python", "-m", "knct_hub"]
