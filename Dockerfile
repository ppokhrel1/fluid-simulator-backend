# --------- Builder Stage ---------
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Builder stage working directory
WORKDIR /app

# 1. Copy ONLY the requirements file (for best layer caching)
# If only code changes, this layer is skipped.
COPY requirements.txt /app/requirements.txt

# 2. Create the virtual environment
# We explicitly create the venv first, as uv's 'pip install' command installs into an active or specified environment.
RUN uv venv /app/.venv

# 3. Install dependencies from requirements.txt
# We use the 'uv pip install' command inside the venv's bin directory for explicit control.
RUN --mount=type=cache,target=/root/.cache/uv \
    /app/.venv/bin/uv pip install -r requirements.txt

# 4. Copy the rest of the project source code
COPY . /app

# The "install project in non-editable mode" step from the original is removed
# because requirements.txt usually doesn't include the project itself.
# Your application code is simply copied in the step above.

# --------- Final Stage ---------
FROM python:3.11-slim-bookworm

# Create a non-root user for security
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Copy the virtual environment from the builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy the application source code
COPY --from=builder --chown=app:app /app /code

# Ensure the virtual environment is in the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Switch to the non-root user and set the working directory
USER app
WORKDIR /code

# -------- Entry Point --------
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]