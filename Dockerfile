FROM python:3.11-slim

LABEL maintainer="LiQUiD SOUND <build@liquidsound.io>"
LABEL description="SENTINEL — Real-time Solana token intelligence"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash sentinel
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright chromium (for NOVA/scrapling)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy source
COPY --chown=sentinel:sentinel . .

# Switch to non-root
USER sentinel

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default entrypoint: listener
# ENTRYPOINT ["python"]
CMD ["python", "sentinel_ph2.py"]
