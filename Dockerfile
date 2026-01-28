# Use Python 3.12 slim image (matches backend/pyproject requires-python)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements first (for Docker layer caching)
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# Layout:
# /app/backend  -> python package + main entrypoint
# /app/dataset.json, /app/models -> data + optional model artifacts
COPY backend/ ./backend/
COPY dataset.json ./dataset.json
COPY models/ ./models/

# Create temp directory for models (Cloud Run ephemeral storage)
RUN mkdir -p /tmp/models

RUN python -c "import tensorflow_hub as hub; print('Downloading USE model...'); hub.load('https://tfhub.dev/google/universal-sentence-encoder/4'); print('USE model cached!')"

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /tmp/models

# Switch to non-root user
USER appuser

# Expose port 8080 (Cloud Run uses this by default)
EXPOSE 8080

# Health check (optional, but good practice)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run with gunicorn (production-ready WSGI server)
# Workers=1 to avoid memory issues, threads=4 for concurrency
# Timeout=300 (5 min) for model loading on cold starts
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "300", "--preload", "backend.main:app"]
