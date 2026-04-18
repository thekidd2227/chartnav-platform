# Production-oriented image.
# Single stage is fine here — dependencies are pure Python wheels.
FROM python:3.11-slim

# Safer Python defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Minimal runtime deps (curl for healthcheck only).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for better layer caching.
COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install -e ".[postgres]"

# App code.
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts_seed.py ./
COPY scripts ./scripts
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh ./scripts/smoke.sh

# Non-root runtime.
RUN useradd --create-home --uid 1001 chartnav \
    && chown -R chartnav:chartnav /app
USER chartnav

ENV API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --retries=6 --start-period=10s \
    CMD curl -fsS "http://127.0.0.1:${API_PORT}/health" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
