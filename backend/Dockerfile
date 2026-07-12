# ── Base image ────────────────────────────────────────────────
# Python 3.11 slim — smaller than full image, has what we need
FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────
# libgomp1: required by sentence-transformers for parallel processing
# gcc: required to compile some Python packages
RUN apt-get update && apt-get install -y \
    libgomp1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────
# Copy requirements first — Docker caches this layer
# So if only app code changes, pip install is skipped (faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Pre-download the embedding model ─────────────────────────
# This bakes the model into the image so Render doesn't
# download 90MB on every cold start (which would time out)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Copy application code ─────────────────────────────────────
COPY app/ ./app/

# ── Create required directories ───────────────────────────────
RUN mkdir -p /app/uploads /app/chroma_db

# ── Expose port ───────────────────────────────────────────────
EXPOSE 8000

# ── Health check ──────────────────────────────────────────────
# Render uses this to verify the container is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')" || exit 1

# ── Start command ─────────────────────────────────────────────
# host=0.0.0.0 required — default 127.0.0.1 is not accessible from outside
# workers=1 for free tier (limited RAM)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]