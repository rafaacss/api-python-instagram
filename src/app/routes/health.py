from flask import Blueprint, jsonify
bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    return jsonify({"code": 200, "payload": "OK"})
