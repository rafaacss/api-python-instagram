import os
import logging
from flask import Blueprint, send_from_directory, abort, current_app

logger = logging.getLogger(__name__)

bp = Blueprint("static_files", __name__)
ALLOWED_EXTENSIONS = {'.json', '.js', '.html', '.css', '.jpg', '.png', '.gif', '.webp', '.mp4', '.mov'}


def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@bp.get("/static/instagram/<path:filename>")
def serve_static_instagram(filename):
    logger.info(f"Servindo arquivo estático: {filename}")

    if not allowed_file(filename):
        logger.warning(f"Extensão não permitida: {filename}")
        abort(404)

    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../static/instagram"))

        # Validar que o arquivo está realmente dentro do diretório permitido
        requested_path = os.path.abspath(os.path.join(base_dir, filename))
        if not requested_path.startswith(base_dir):
            logger.error(f"Tentativa de path traversal: {filename}")
            abort(403)

        logger.info(f"Enviando: {requested_path}")
        return send_from_directory(base_dir, filename)
    except Exception as e:
        logger.error(f"Erro ao servir arquivo estático: {e}", exc_info=True)
        abort(500)


# Endpoint alternativo para servir JSON mockado
@bp.get("/api/mock/posts")
def mock_posts():
    """Endpoint para servir dados mockados de posts para testes"""
    logger.info("Servindo dados mockados")
    try:
        json_file = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../../../static/instagram/mock_posts.json"
        ))

        if not os.path.exists(json_file):
            logger.warning(f"Arquivo mock não encontrado: {json_file}")
            return {"code": 200, "payload": []}, 200

        return send_from_directory(os.path.dirname(json_file), "mock_posts.json")
    except Exception as e:
        logger.error(f"Erro ao servir mock posts: {e}", exc_info=True)
        return {"code": 500, "error": str(e)}, 500