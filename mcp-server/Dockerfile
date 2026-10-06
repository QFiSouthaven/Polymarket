# syntax=docker/dockerfile:1
#
# Multi-stage build for polyagent-mcp-server
# Build on Python 3.14 (matches Falki's host version)
#
# Usage: docker build -t polyagent-mcp-server F:/PolyMarket/mcp-server/
#        docker run --rm -it -v F:/PolyMarket/mcp-server/dev_state.db:/app/dev_state.db polyagent-mcp-server
#

# ─── Stage 1: Build ───────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy project metadata
COPY pyproject.toml README.md ./

# Install build deps
RUN pip install --no-cache-dir build

# Build the wheel (resolves dependencies from pyproject.toml)
RUN python -m build --wheel

# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

WORKDIR /app/mcp-server

# Copy built wheel and install deps
COPY --from=builder /build/dist/*.whl ./

RUN pip install --no-cache-dir --root-user-action=ignore . && \
    pip uninstall -y build setuptools

# Copy source
COPY src/ ./src/

# Create data directory (dev_state.db lives here)
RUN mkdir -p /app/dev_state && chmod 1777 /app/dev_state

# Set Python path so `python -m mcp_server.server` works
ENV PYTHONPATH=/app/mcp-server/src
ENV MCP_SERVER_CONFIG=/app/mcp-server/config.yaml

# Healthcheck (check if the server starts without crashing)
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import mcp_server; print('ok')" || exit 1

# Entrypoint
ENTRYPOINT ["python", "-m", "mcp_server.server"]
