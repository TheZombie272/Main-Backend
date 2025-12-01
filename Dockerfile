FROM python:3.14-slim

# Do not write .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Ensure logs are sent straight to terminal (no buffering)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for some Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer cache
COPY requirements.txt ./

# Upgrade pip and install Python dependencies
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . /app

# Create a non-root user and use it
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Expose the application port
EXPOSE 8000

# Default envs (can be overridden at runtime)
ENV PORT=8000

# Run the app with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
