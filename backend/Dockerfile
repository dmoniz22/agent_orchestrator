FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi uvicorn pydantic pydantic-settings \
    httpx sqlalchemy asyncpg \
    pyyaml structlog python-multipart

# Copy backend source
COPY backend/src ./src
COPY backend/tests ./tests
COPY CONFIG ./CONFIG

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]