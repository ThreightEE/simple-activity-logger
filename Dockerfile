# Slim variant as parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements to utilize Docker cache
COPY requirements.txt /app/
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . /app/

# Set Python environment variables for performance
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000