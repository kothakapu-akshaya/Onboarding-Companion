# Use Python 3.13 slim image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Create a non-root user and group for security
RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin -c "Docker image user" appuser

WORKDIR /app

# Copy project files and app directory for build
COPY pyproject.toml uv.lock README.md ./
COPY app/ ./app/

# Install dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application code
COPY . .

RUN chmod +x init_db.py

# Create necessary directories and set permissions
RUN mkdir -p /tmp/chunks /tmp/staging /tmp/logs && \
    chown -R appuser:appuser /tmp/chunks /tmp/staging /tmp/logs && \
    chmod 755 /tmp/chunks /tmp/staging /tmp/logs

# Ensure /tmp has proper permissions for appuser
RUN chmod 1777 /tmp

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app

# Create uv cache directory with proper permissions
RUN mkdir -p /home/appuser/.cache/uv && \
    chown -R appuser:appuser /home/appuser/.cache

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Default command to run the application with Gunicorn
CMD ["uv", "run", "gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-w", "4", "-b", "0.0.0.0:8000"]
