# ==========================================
# Stage 1: Sanity Check, Compilation & Unit Tests
# ==========================================
FROM python:3.12-slim AS test-runner

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/workspace

# Sanity Gate 1: Bytecode Compilation Check
RUN python3 -m py_compile app/main.py app/config.py && \
    echo ">> [CI-SANITY] Compilation check passed successfully."

# Sanity Gate 2: Runtime Unit Tests Execution
RUN pytest -v --tb=short tests/test_api.py && \
    echo ">> [CI-SANITY] All runtime unit tests passed successfully."

# ==========================================
# Stage 2: Minimal Hardened Production Image
# ==========================================
FROM python:3.12-slim AS runtime

# Security best practice: Create non-root user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -d /app appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

COPY --chown=appuser:appgroup app/ ./app

# Set non-root user
USER appuser

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PYTHONPATH=/app

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
