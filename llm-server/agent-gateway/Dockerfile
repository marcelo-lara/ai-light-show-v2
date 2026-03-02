# ---- Base image ----
FROM python:3.11-slim

# ---- System dependencies ----
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Workdir ----
WORKDIR /app

# ---- Python dependencies ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy source ----
COPY . .

# ---- Runtime environment ----
ENV PYTHONUNBUFFERED=1
ENV LLM_BASE_URL=http://llm-server:8080
ENV MCP_BASE_URL=http://mcp-server:7000

# ---- Expose FastAPI port ----
EXPOSE 8090

# ---- Run server ----
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]