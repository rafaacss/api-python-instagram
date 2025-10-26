# syntax=docker/dockerfile:1.6
FROM python:3.12-slim

ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/poetry/bin:/app/.venv/bin:$PATH" \
    PORT=8000

# deps básicos
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# instala Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# só manifests para cache
COPY pyproject.toml poetry.lock* /app/

# instala deps + o próprio pacote (SEM --no-root)
# IMPORTANTE: para layout src/, o pyproject precisa ter:
# packages = [{ include = "app", from = "src" }]
RUN poetry install --only main --no-ansi

# copia o código
COPY src ./src
COPY wsgi.py ./wsgi.py

EXPOSE 8000

# Flask é WSGI → Gunicorn basta
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "wsgi:app"]
