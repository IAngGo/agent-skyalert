FROM python:3.12-slim

# Install system dependencies for psycopg2 and Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser
RUN playwright install chromium --with-deps

# Copy application source
COPY . .

# Default command — overridden by docker-compose.yml per service
CMD ["uvicorn", "backend.infrastructure.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
