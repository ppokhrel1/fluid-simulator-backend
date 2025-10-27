# --------- Builder Stage ---------
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install build tools for compiled wheels (only in builder)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Create virtualenv and install requirements without using pip cache
RUN python -m venv /opt/venv \
 && /opt/venv/bin/python -m pip install --upgrade pip setuptools wheel \
 && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

# Copy project files afterwards (so deps layer remains cached)
COPY . /app

# If you need to "install" the package locally (optional)
# RUN /opt/venv/bin/pip install --no-cache-dir .

# --------- Final Stage ---------
FROM python:3.11-slim-bookworm

# create non-root user
RUN groupadd --gid 1000 app \
 && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# copy venv from builder stage
COPY --from=builder --chown=app:app /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PIP_NO_CACHE_DIR=1

USER app
WORKDIR /code

# expose the Cloud Run default port (optional; for clarity)
EXPOSE 8080

# Use the PORT env var (fallback 8080) so Cloud Run can route traffic correctly.
# The 'exec' wrapped in sh -c ensures the uvicorn process receives signals properly.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
