# syntax=docker/dockerfile:1.6

########### STAGE 1: build do widget (Vue + Vite + Tailwind) ###########
FROM node:20-alpine AS widget-build

# Onde o widget vive dentro do projeto
WORKDIR /app

# Copiamos só o mínimo para aproveitar cache
# (ajuste os caminhos se seu layout for diferente)
# Estrutura esperada:
# src/app/static/feeds/
#   ├─ package.json
#   ├─ vite.config.js
#   ├─ tailwind.config.js
#   ├─ index.html
#   └─ src/...
COPY src/app/static/feeds/package.json src/app/static/feeds/yarn.lock* ./src/app/static/feeds/
WORKDIR /app/src/app/static/feeds

# Yarn moderno via corepack
RUN corepack enable && \
    corepack prepare yarn@stable --activate

# Instala dependências do front
RUN yarn install --frozen-lockfile

# Copiamos o restante dos arquivos do widget e buildamos
COPY src/app/static/feeds/ ./
RUN yarn build

# Ao final, teremos /app/src/app/static/feeds/dist


########### STAGE 2: API Python ###########
FROM python:3.12-slim AS api

ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/poetry/bin:/app/.venv/bin:$PATH" \
    \
    INSTAGRAM_APP_ID="1335809461025995" \
    INSTAGRAM_APP_SECRET="9e9bbaadb87346862d203a85f3350e15" \
    INSTAGRAM_ACCESS_TOKEN="IGAASZB6WBpfMtBZAE5ybDl3RkV4SEJEVDYxV0V5RDljUmJTV3FodlhzZA2dRMmFMcXFyVjhJV3F0d2lrZAmxUVDUwNmdYZA2ZACcG9mck0zM1d2aFFSeERiWjM0YjR1ZAlNNYW9YS1llc3NDekdwWGN1cno1V2s1R3k2VmcyWUk0T1Y1YwZDZD" \
    INSTAGRAM_BUSINESS_ACCOUNT_ID="17841405297932427" \
    \
    GOOGLE_PLACE_ID="ChIJARIUHE0tWpMRHrYqZJ2w8sE" \
    GOOGLE_API_KEY="AIzaSyB4eHFNIGWpCGUpHAGODpR_dvWygj7pgtw" \
    \
    CACHE_DURATION_SECONDS=3600 \
    MEDIA_CACHE_TTL_SECONDS=3600 \
    MEDIA_CACHE_DIR="/var/cache/igmedia" \
    MEDIA_CACHE_MAX_BYTES="26214400" \
    WARMUP_TOKEN="d7a36c345c9cfe7d786086a72d755f4e40856b39" \
    WARMUP_SLEEP_SECONDS="0.25" \
    API_BASE_URL="http://localhost:8080"

# ⚠️ Se possível, mova essas chaves para variáveis em tempo de deploy (docker compose / secrets)
# em vez de baked-in na imagem.

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# 1) Só manifests → cache de dependências
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main --no-ansi --no-root

# 2) Código da API
COPY src ./src
COPY src/app/static ./static
COPY wsgi.py ./wsgi.py

# 3) Copiamos o build do widget do Stage 1 para o local servido pelo Flask
#    (/app/static/feeds/dist)
COPY --from=widget-build /app/src/app/static/feeds/dist ./static/feeds/dist

# 4) Instala o PRÓPRIO pacote agora que o código existe
RUN poetry install --only main --no-ansi

ENV PYTHONPATH="/app/src:$PYTHONPATH"

EXPOSE 8000

# ⚠️ Corrigido para usar o .venv gerenciado pelo Poetry (o caminho correto está no PATH)
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
