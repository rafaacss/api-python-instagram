# src/app/routes/admin.py
from flask import Blueprint, jsonify, request, current_app
from ..services.cache import clear_memory_cache
from ..services.media_cache import clear_media_cache_all, drop_media_cache
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("admin", __name__)


@bp.post("/api/admin/clear_cache")
def clear_cache_route():
    """
    Endpoint para limpar cache
    Parâmetros:
    - token: Token de autorização
    - what: 'all', 'memory', ou 'media'
    """
    token = request.headers.get("X-Warmup-Token") or request.args.get("token", "")
    cfg = current_app.config

    logger.info(f"clear_cache_route chamado")

    # Validar token
    if cfg.get("WARMUP_TOKEN"):
        if token != cfg["WARMUP_TOKEN"]:
            logger.warning("Token inválido")
            return jsonify({"error": "unauthorized"}), 401
    else:
        # Se não há token configurado, permite apenas de localhost
        remote = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
        if not (remote.startswith('127.') or remote == '::1'):
            logger.warning(f"Acesso negado de {remote}")
            return jsonify({"error": "forbidden"}), 403

    what = (request.args.get("what") or (request.json.get("what") if request.is_json else "all")).lower()
    media_id = (request.args.get("media_id") or (request.json.get("media_id") if request.is_json else "")).strip()

    logger.info(f"clear_cache_route: what={what}, media_id={media_id}")

    result = {}

    if what in ("all", "memory"):
        clear_memory_cache()
        result["memory"] = "cleared"
        logger.info("Cache de memória limpo")

    if what in ("all", "media"):
        result["media"] = clear_media_cache_all()
        logger.info(f"Cache de mídia limpo: {result['media']}")

    if what == "media_id":
        if not media_id:
            logger.error("media_id ausente")
            return jsonify({"error": "missing media_id"}), 400
        drop_media_cache(media_id)
        result["media_id"] = {"id": media_id, "status": "cleared"}
        logger.info(f"Cache de mídia específica limpo: {media_id}")

    if not result:
        logger.error(f"Parâmetro 'what' inválido: {what}")
        return jsonify({"error": "invalid 'what' (use all|memory|media|media_id)"}), 400

    return jsonify({"code": 200, "payload": result})