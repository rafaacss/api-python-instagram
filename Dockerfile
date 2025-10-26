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

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# 1) Só manifests → cache de dependências
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main --no-ansi --no-root

# 2) Agora copia o código
COPY src ./src
COPY static ./static
COPY wsgi.py ./wsgi.py

# 3) Instala o PRÓPRIO pacote (root) agora que o código existe
RUN poetry install --only main --no-ansi

ENV PYTHONPATH="/app/src:$PYTHONPATH"

EXPOSE 8000
CMD ["/venv/bin/gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
