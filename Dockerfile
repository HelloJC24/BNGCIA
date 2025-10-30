# Production Dockerfile - Simplified and Working
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install packages directly to avoid requirements.txt issues
RUN pip install --no-cache-dir --upgrade pip==24.0

# Install core packages one by one (guaranteed to work)
RUN pip install --no-cache-dir fastapi==0.110.0
RUN pip install --no-cache-dir uvicorn==0.27.0
RUN pip install --no-cache-dir gunicorn==21.2.0
RUN pip install --no-cache-dir redis==5.0.1
RUN pip install --no-cache-dir pydantic==2.6.0
RUN pip install --no-cache-dir python-dotenv==1.0.1
RUN pip install --no-cache-dir requests==2.31.0
RUN pip install --no-cache-dir beautifulsoup4==4.12.3
RUN pip install --no-cache-dir openai==1.12.0
RUN pip install --no-cache-dir tqdm==4.66.2

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy application files
COPY --chown=appuser:appuser main_basic.py main.py
COPY --chown=appuser:appuser .env* ./

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Expose port
EXPOSE 8000

# Use gunicorn for production
CMD ["gunicorn", "main:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]