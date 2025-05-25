# Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    azure-search-documents==11.4.0 \
    python-dotenv==1.0.0

COPY . .

CMD ["python", "mcp_server.py"]
