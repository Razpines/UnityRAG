FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UNITY_DOCS_MCP_ROOT=/app \
    UNITY_DOCS_MCP_CONFIG=/app/config.docker.yaml \
    UNITY_DOCS_MCP_HOST=0.0.0.0 \
    UNITY_DOCS_MCP_PORT=8765

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY config.yaml config.docker.yaml ./
COPY src ./src

RUN python -m pip install --upgrade pip && \
    python -m pip install .

EXPOSE 8765

VOLUME ["/app/data"]

CMD ["unitydocs-mcp-http"]
