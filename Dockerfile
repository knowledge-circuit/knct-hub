# syntax=docker/dockerfile:1.7

# --- Stage 1: build dashboard ---
FROM node:22-alpine AS dashboard-build
RUN corepack enable
WORKDIR /app/dashboard
COPY dashboard/package.json dashboard/pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --ignore-scripts --config.minimumReleaseAge=0
COPY dashboard ./
RUN pnpm run build

# --- Stage 2: server runtime ---
FROM python:3.12-slim AS server
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.source="https://github.com/knowledge-circuit/knct-hub" \
      org.opencontainers.image.description="knct-hub — smart context injection for AI coding agents." \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.title="knct-hub" \
      org.opencontainers.image.url="https://github.com/knowledge-circuit/knct-hub" \
      org.opencontainers.image.documentation="https://github.com/knowledge-circuit/knct-hub#readme"

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
