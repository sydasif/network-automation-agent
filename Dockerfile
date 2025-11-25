# Use official Python 3.12 slim image (Lightweight)
FROM python:3.12-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Ensures logs are streamed to console immediately (Vital for Chainlit)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory inside the container
WORKDIR /app

# Install system dependencies
# 'git' is often required by Nornir plugins or for downloading ntc-templates
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker Layer Caching optimization)
# If you change code but not requirements, Docker skips this step on rebuilds
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the default Chainlit port
EXPOSE 8000

# Command to run the application
# -w: Watch mode (reloads on code changes)
# --host 0.0.0.0: Required to access the app from outside the container
CMD ["chainlit", "run", "app.py", "-w", "--port", "8000", "--host", "0.0.0.0"]