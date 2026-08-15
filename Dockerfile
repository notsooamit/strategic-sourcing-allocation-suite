# Base image: Python 3.11 Debian Slim
FROM python:3.11-slim

# Install CBC linear programming solver and system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    coinor-cbc \
    coinor-libcbc-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY . .

# Generate initial dataset if needed
RUN python scripts/generate_synthetic_data.py

# Expose HTTP port
EXPOSE 8000
ENV PORT=8000

# Start enterprise platform
CMD ["python", "run_server.py"]
