# ══════════════════════════════════════════════════════════════
# Dockerfile - Bewerbungs-Tool
# ══════════════════════════════════════════════════════════════
#
# Build:   docker build -t bewerbung-tool .
# Run:     docker run -p 8000:8000 bewerbung-tool
#
# ══════════════════════════════════════════════════════════════

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --no-cache-dir --user fastapi uvicorn jinja2

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Non-root user für Security
RUN useradd --create-home --shell /bin/bash appuser

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY src/ ./src/
COPY templates/ ./templates/
COPY config/settings.yaml ./config/

# Create directories for runtime data
RUN mkdir -p /app/config /app/attachments \
    && chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Default: Web server (später)
# Für CLI: docker run bewerbung-tool python src/bewerbung.py --list
CMD ["uvicorn", "src.web:app", "--host", "0.0.0.0", "--port", "8000"]

# ══════════════════════════════════════════════════════════════
# Labels
# ══════════════════════════════════════════════════════════════
LABEL maintainer="Wolfram Laube <wolfram.laube@blauweiss-edv.at>"
LABEL version="1.0.0"
LABEL description="Automatisiertes Bewerbungs-Tool"
