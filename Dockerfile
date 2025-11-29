# Use official Python 3.12 slim image (Lightweight)
FROM python:3.12-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Ensures logs are streamed to console immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory inside the container
WORKDIR /app

# Install system dependencies
# 'git' is often required by Nornir plugins or for downloading ntc-templates
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first (Docker Layer Caching optimization)
# If you change code but not dependencies, Docker skips this step on rebuilds
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application code
COPY . .

# Default command to run the application in interactive chat mode
# Use: docker run -it <image> or docker compose run -it network-agent-cli
CMD ["python", "main.py", "--chat"]