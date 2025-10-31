# syntax=docker/dockerfile:1.6
FROM python:3.12-slim

ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/poetry/bin:/app/.venv/bin:$PATH" \

    INSTAGRAM_APP_ID="1335809461025995" \
    INSTAGRAM_APP_SECRET="9e9bbaadb87346862d203a85f3350e15" \
    INSTAGRAM_ACCESS_TOKEN="IGAASZB6WBpfMtBZAE5ybDl3RkV4SEJEVDYxV0V5RDljUmJTV3FodlhzZA2dRMmFMcXFyVjhJV3F0d2lrZAmxUVDUwNmdYZA2ZACcG9mck0zM1d2aFFSeERiWjM0YjR1ZAlNNYW9YS1llc3NDekdwWGN1cno1V2s1R3k2VmcyWUk0T1Y1YwZDZD" \
    INSTAGRAM_BUSINESS_ACCOUNT_ID="17841405297932427" \

    GOOGLE_PLACE_ID="ChIJARIUHE0tWpMRHrYqZJ2w8sE" \
    GOOGLE_API_KEY="AIzaSyB4eHFNIGWpCGUpHAGODpR_dvWygj7pgtw" \

    CACHE_DURATION_SECONDS=3600 \
    MEDIA_CACHE_TTL_SECONDS=3600 \
    MEDIA_CACHE_DIR="/var/cache/igmedia" \
    MEDIA_CACHE_MAX_BYTES="26214400" \
    WARMUP_TOKEN="d7a36c345c9cfe7d786086a72d755f4e40856b39" \
    WARMUP_SLEEP_SECONDS="0.25" \
    API_BASE_URL="http://localhost:8080"

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
COPY src/app/static ./static
COPY wsgi.py ./wsgi.py

# 3) Instala o PRÓPRIO pacote (root) agora que o código existe
RUN poetry install --only main --no-ansi

ENV PYTHONPATH="/app/src:$PYTHONPATH"

EXPOSE 8000
CMD ["/venv/bin/gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
