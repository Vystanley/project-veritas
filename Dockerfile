# Dockerfile — Veritas backend
# Produces a self-contained image with Python 3.11, ffmpeg, and all app dependencies.
# Used by Render (docker runtime), but equally runnable on Fly.io, Railway, Docker Desktop, etc.

FROM python:3.11-slim

# System packages: ffmpeg (for video/audio extraction) + curl (for health checks)
# Clean apt cache in the same layer to keep the image small.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      curl \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (benefits Docker layer caching on code-only changes).
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
       --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/

# Copy the application code.
COPY backend /app

# Render sets $PORT for us. Default to 8000 for local docker runs.
ENV PORT=8000
EXPOSE 8000

# Use shell form so $PORT expands at container start.
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT}
