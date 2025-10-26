# src/app/__init__.py
import os
from flask import Flask
from .config import Settings
from .extensions import init_extensions
from .routes.instagram import bp as instagram_bp
from .routes.google import bp as google_bp
from .routes.health import bp as health_bp
from .routes.static_files import bp as static_bp


def create_app():
    os.makedirs(Settings.MEDIA_CACHE_DIR, exist_ok=True)
    app = Flask(__name__, static_folder='static')
    app.config.from_object(Settings)
    init_extensions(app)

    app.register_blueprint(instagram_bp, url_prefix="/api/instagram")
    app.register_blueprint(google_bp,    url_prefix="/api/google")
    app.register_blueprint(health_bp)
    app.register_blueprint(static_bp)
    return app
