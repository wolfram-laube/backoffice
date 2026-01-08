# ══════════════════════════════════════════════════════════════
# Dockerfile - Freelancer Admin
# ══════════════════════════════════════════════════════════════

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --no-cache-dir --user fastapi uvicorn jinja2

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY modules/ ./modules/
COPY common/ ./common/
COPY config/settings.yaml ./config/
COPY cli.py .

RUN mkdir -p /app/config /app/attachments \
    && chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

# Default: Web server (später)
CMD ["uvicorn", "modules.applications.web:app", "--host", "0.0.0.0", "--port", "8000"]

LABEL maintainer="Wolfram Laube <wolfram.laube@blauweiss-edv.at>"
LABEL version="1.1.0"
LABEL description="Freelancer Admin - Modulares Tool für Bewerbungen, Rechnungen, Timesheets"
