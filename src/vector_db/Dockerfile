FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8004

# Run the application
CMD ["python", "-m", "uvicorn", "src.vector_db.v1.main:app", "--host", "0.0.0.0", "--port", "8004"]