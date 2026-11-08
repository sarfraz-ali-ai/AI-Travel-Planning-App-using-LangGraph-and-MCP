FROM python:3.13-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip FIRST so it recognizes Python 3.13 wheels
RUN pip install --upgrade pip

COPY requirements.txt .

# Install Python dependencies (xxhash should now find its wheel)
RUN pip install --no-cache-dir -r requirements.txt

# Install the original AviationStack MCP server
RUN pip install --no-cache-dir aviationstack-mcp

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]