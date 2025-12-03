# syntax=docker/dockerfile:1

# --- Base image with Python and system tools
FROM python:3.11-slim AS base

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime deps: nmap for scanning, graphviz for diagrams, curl for healthchecks
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       nmap graphviz curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code
COPY backend /app

# Static frontend files are expected in /app/static (optional)
# Use build script to place Flutter web build here before building image, or
# mount at runtime.

EXPOSE 8000

# Default command: start uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]