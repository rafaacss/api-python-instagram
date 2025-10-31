# syntax=docker/dockerfile:1.6

#############################
# STAGE 1: Build do Widget  #
#############################
FROM node:20-alpine AS widget-build

# Ativa Yarn 4 (Berry)
RUN corepack enable && corepack prepare yarn@4.10.3 --activate

# Diretório do widget (ajuste se necessário)
WORKDIR /app/src/app/static/feeds

# Copiamos manifestos primeiro para cache de dependências
COPY src/app/static/feeds/package.json ./
# Se houver yarn.lock no repo, ele será copiado; se não houver, a linha ignorada não falha
COPY src/app/static/feeds/yarn.lock* ./

# Instalação condicional:
# - Se houver yarn.lock → instalação reprodutível (--immutable)
# - Se não houver → primeira instalação gera lockfile
RUN if [ -f yarn.lock ]; then \
      yarn install --immutable; \
    else \
      yarn install; \
    fi

# Copia o restante do widget e faz o build
COPY src/app/static/feeds/ ./
RUN yarn build
# Resultado em: /app/src/app/static/feeds/dist


#############################
# STAGE 2: API Python       #
#############################
FROM python:3.12-slim AS api

# ---- Ambiente Poetry/Python ----
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/poetry/bin:/app/.venv/bin:$PATH"

# ---- Variáveis do app (ideal mover para secrets/compose em produção) ----
ENV INSTAGRAM_APP_ID="1335809461025995" \
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

# Dependências de sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instala Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# 1) Só manifests → cache de deps
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --only main --no-ansi --no-root

# 2) Código da API
COPY src ./src
COPY src/app/static ./static
COPY wsgi.py ./wsgi.py

# 3) Copia o build do widget do Stage 1 para onde o Flask serve
#    (seu static_files.py já aponta para static/feeds/dist)
COPY --from=widget-build /app/src/app/static/feeds/dist ./static/feeds/dist

# 4) Instala o pacote do projeto (agora que o código existe)
RUN poetry install --only main --no-ansi

ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Porta do Gunicorn
EXPOSE 8000

# Usa o .venv do Poetry (já no PATH)
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120"]
