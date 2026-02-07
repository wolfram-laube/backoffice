# Match Staging Service — Multi-stage Docker build
# Target: GCP Cloud Run (same pattern as MAB service)

FROM python:3.12-slim AS base

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# --- Dependencies ---
FROM base AS deps
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[whatsapp]"

# --- Runtime ---
FROM deps AS runtime
COPY src/ src/
COPY config/ config/

EXPOSE 8080

# Cloud Run sets PORT env var
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
