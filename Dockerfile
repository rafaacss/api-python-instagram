# Base de runtime + build (usa slim para ficar leve)
FROM python:3.11-slim

# ---- Sistema e Poetry ----
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=true \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/poetry/bin:/venv/bin:$PATH" \
    VIRTUAL_ENV="/venv" \
    PORT=8000

# Dependências de build (removidas depois)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Instala Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    python -m venv /venv

WORKDIR /app

# Copia manifestos do Poetry primeiro para cache de deps
COPY pyproject.toml poetry.lock* /app/

# Instala deps de produção no venv
RUN poetry config virtualenvs.path /venv && \
    poetry install --only main --no-interaction --no-ansi --no-root && \
    # Servidor ASGI
    pip install --no-cache-dir gunicorn uvicorn

# Copia o restante do código
COPY . /app

# (Opcional) Se seu pacote é instalável, habilite:
# RUN poetry install --only main --no-interaction --no-ansi

# Ajuste o módulo/objeto ASGI abaixo se necessário (ex.: src.main:app)
CMD ["/venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
