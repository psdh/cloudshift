# Multi-stage build for CloudShift Backend

# Stage 1: Builder
FROM python:3.10-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create the non-root user BEFORE copying deps so they land in a home the
# runtime user can actually read. (The deps were pip-installed with --user
# into the builder's /root/.local; copying that to /root/.local and then
# switching to a non-root user made every dependency unreadable -> the
# container could not start at all.)
RUN useradd -m -u 1000 cloudshift

# Copy Python dependencies from builder into the runtime user's home
COPY --from=builder --chown=cloudshift:cloudshift /root/.local /home/cloudshift/.local

# Copy application code
COPY --chown=cloudshift:cloudshift . .

# Make sure scripts are executable
RUN chmod +x /app/scripts/*.sh 2>/dev/null || true

# Add the user-local bin to PATH
ENV PATH=/home/cloudshift/.local/bin:$PATH

USER cloudshift

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
