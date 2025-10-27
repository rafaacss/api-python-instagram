# src/app/routes/admin.py
from flask import Blueprint, jsonify, request, current_app
from ..services.cache import clear_memory_cache
from ..services.media_cache import clear_media_cache_all

bp = Blueprint("admin", __name__)

@bp.post("/api/admin/clear_cache")
def clear_cache_route():
    token = request.headers.get("X-Warmup-Token") or request.args.get("token", "")
    cfg = current_app.config
    if cfg.get("WARMUP_TOKEN") and token != cfg["WARMUP_TOKEN"]:
        return jsonify({"error": "unauthorized"}), 401

    what = (request.args.get("what") or (request.json.get("what") if request.is_json else "all")).lower()
    result = {}
    if what in ("all", "memory"):
        clear_memory_cache()
        result["memory"] = "cleared"
    if what in ("all", "media"):
        result["media"] = clear_media_cache_all()
    if not result:
        return jsonify({"error": "invalid 'what' (use all|memory|media)"}), 400
    return jsonify({"code": 200, "payload": result})
