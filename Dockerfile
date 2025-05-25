# Use official Python image
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y build-essential git curl

# Set work directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose service port (for FastAPI)
EXPOSE 8001

# Set environment variables for production (these can be overridden at deploy time)
ENV PYTHONUNBUFFERED=1

# Default: launch vector-enabled API (mcp_server_sota)
CMD ["uvicorn", "mcp_server_sota:app", "--host", "0.0.0.0", "--port", "8001"]
