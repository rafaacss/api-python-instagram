# src/app/__init__.py
import os
import logging
from flask import Flask
from .config import Settings
from .extensions import init_extensions

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    logger.info("Iniciando criação da aplicação Flask")

    os.makedirs(Settings.MEDIA_CACHE_DIR, exist_ok=True)
    logger.info(f"Diretório de cache criado/verificado: {Settings.MEDIA_CACHE_DIR}")

    app = Flask(__name__, static_folder='static')
    app.config.from_object(Settings)

    logger.info(f"API_BASE_URL: {Settings.API_BASE_URL}")
    logger.info(f"CACHE_DURATION_SECONDS: {Settings.CACHE_DURATION_SECONDS}")
    logger.info(f"MEDIA_CACHE_TTL_SECONDS: {Settings.MEDIA_CACHE_TTL_SECONDS}")
    logger.info(f"MEDIA_CACHE_MAX_BYTES: {Settings.MEDIA_CACHE_MAX_BYTES}")

    init_extensions(app)
    logger.info("Extensões inicializadas (CORS)")

    # imports LAZY (aqui dentro)
    logger.info("Importando blueprints")
    from .routes.instagram import bp as instagram_bp
    from .routes.google import bp as google_bp
    from .routes.health import bp as health_bp
    from .routes.static_files import bp as static_bp
    from .routes.admin import bp as admin_bp

    app.register_blueprint(instagram_bp, url_prefix="/api/instagram")
    app.register_blueprint(google_bp, url_prefix="/api/google")
    app.register_blueprint(health_bp)
    app.register_blueprint(static_bp)
    app.register_blueprint(admin_bp)

    logger.info("Blueprints registrados com sucesso")
    logger.info("Aplicação Flask criada com sucesso")

    return app