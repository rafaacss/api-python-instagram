import os
from flask import Blueprint, send_from_directory, abort

bp = Blueprint("static_files", __name__)
ALLOWED_EXTENSIONS = {'.json', '.js', '.html', '.css', '.jpg', '.png'}

def allowed_file(filename): return os.path.splitext(filename)[1] in ALLOWED_EXTENSIONS

@bp.get("/static/instagram/<path:filename>")
def serve_static_instagram(filename):
    if not allowed_file(filename): abort(404)
    return send_from_directory('static/instagram', filename)
