FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health' if 'WEBHOOK' in open('/proc/1/environ').read() else 'file:///dev/null', timeout=2)" || exit 1

CMD ["python", "-m", "src.main"]