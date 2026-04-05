# ── Stage 1: Build ──
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build-time system dependencies (compilers + geospatial dev headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libspatialindex-dev gcc g++ \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──
FROM python:3.11-slim

WORKDIR /app

# Runtime-only system libraries (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libspatialindex6 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

EXPOSE 8080

# Streamlit environment
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_ENABLE_CORS=true
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION=false
ENV STREAMLIT_SERVER_RUN_ON_SAVE=false
ENV STREAMLIT_RUNNER_MAGIC_ENABLED=false

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

CMD ["streamlit", "run", "run_leaflet.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableWebsocketCompression=false", "--server.enableCORS=true", "--server.enableXsrfProtection=false", "--runner.magicEnabled=false"]
