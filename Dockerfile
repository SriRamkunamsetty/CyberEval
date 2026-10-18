# =========================================================================
# CyberEval - Production Container Dockerfile
# =========================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for rapid dependency resolution
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml .
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN uv pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy aiosqlite greenlet pytest httpx jinja2 python-multipart numpy networkx click

# Final Runtime Image
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user for principle of least privilege
RUN groupadd -r cybereval && useradd -r -g cybereval cybereval

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY cybereval ./cybereval
COPY frontend ./frontend

# Change ownership
RUN chown -R cybereval:cybereval /app

USER cybereval

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/docs || exit 1

ENTRYPOINT ["uvicorn", "cybereval.main:app", "--host", "0.0.0.0", "--port", "8000"]
