import os
import logging
from flask import Blueprint, send_from_directory, abort, jsonify, make_response

logger = logging.getLogger(__name__)

bp = Blueprint("static_files", __name__)

# ---------------------------------------------------------
# Extensões aceitas (inclui tipos gerados pelo Vite/Tailwind)
# ---------------------------------------------------------
ALLOWED_EXTENSIONS = {
    '.json', '.js', '.mjs', '.html', '.css',
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
    '.mp4', '.webm', '.mov', '.avi',
    '.woff', '.woff2', '.ttf', '.eot',
    '.ico', '.txt', '.map'
}


def allowed_file(filename: str) -> bool:
    """Verifica se a extensão do arquivo é permitida."""
    filename = filename.split('?')[0]
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# ---------------------------------------------------------
# Localização de diretórios estáticos por subpasta
#   subfolder = 'instagram'      -> .../static/instagram
#   subfolder = 'feeds/dist'     -> .../static/feeds/dist
# ---------------------------------------------------------
def get_base_dir(subfolder: str = "instagram") -> str:
    """
    Detecta automaticamente o diretório correto dos arquivos estáticos
    para a subpasta informada.
    """
    candidates = [
        f"src/app/static/{subfolder}",
        f"/app/static/{subfolder}",
        f"/static/{subfolder}",
        f"/app/src/static/{subfolder}",
        f"static/{subfolder}",
        f"./static/{subfolder}",
        os.path.join(os.getcwd(), f"static/{subfolder}"),
    ]

    logger.info("Procurando diretório estático para '%s':", subfolder)
    for path in candidates:
        abs_path = os.path.abspath(path)
        exists = os.path.exists(abs_path)
        logger.info("  - %s %s", abs_path, '✓' if exists else '✗')
        if exists and os.path.isdir(abs_path):
            logger.info("✓ Usando: %s", abs_path)
            return abs_path

    logger.warning("⚠ Nenhum diretório encontrado para '%s', usando padrão: %s", subfolder, candidates[0])
    return os.path.abspath(candidates[0])


def _safe_send(base_dir: str, clean_filename: str):
    """
    Valida traversal, existência e envia arquivo;
    retorna (response, not_found_bool).
    """
    requested_path = os.path.abspath(os.path.join(base_dir, clean_filename))

    # Path traversal
    if not requested_path.startswith(base_dir):
        logger.error("Tentativa de path traversal: %s", clean_filename)
        abort(403)

    # Arquivo existe?
    if not os.path.exists(requested_path):
        logger.warning("Arquivo não encontrado: %s", requested_path)
        try:
            files = os.listdir(base_dir)
            logger.info("Arquivos disponíveis em %s: %s", base_dir, files)
        except Exception as e:
            logger.error("Erro ao listar %s: %s", base_dir, e)
        return None, True

    logger.info("Enviando: %s", requested_path)
    response = make_response(send_from_directory(base_dir, clean_filename))

    # Ajuste de content-type útil
    if clean_filename.endswith('.json'):
        response.headers['Content-Type'] = 'application/json'
    elif clean_filename.endswith('.js') or clean_filename.endswith('.mjs'):
        response.headers['Content-Type'] = 'application/javascript'

    # Cache leve + CORS liberado
    response.headers['Cache-Control'] = 'public, max-age=3600'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response, False


# ======================================================================
# FEEDS (widget Vue compilado em static/feeds/dist)  --------------------
# ======================================================================

@bp.get("/feeds")
def feeds_index():
    """
    SPA do widget (Vite) em static/feeds/dist/index.html
    """
    base_dir = get_base_dir("feeds/dist")
    resp, not_found = _safe_send(base_dir, "index.html")
    if not_found:
        abort(404)
    return resp


@bp.get("/feeds/<path:filename>")
def feeds_assets(filename):
    """
    Arquivos do build (JS/CSS/assets).
    Se não existir, faz fallback para index.html (SPA).
    """
    clean = filename.split('?')[0]
    base_dir = get_base_dir("feeds/dist")

    resp, not_found = _safe_send(base_dir, clean)
    if not_found:
        logger.info("Fallback SPA para /feeds: %s", clean)
        resp2, not_found2 = _safe_send(base_dir, "index.html")
        if not_found2:
            abort(404)
        return resp2
    return resp


@bp.get("/static/feeds/<path:filename>")
def serve_static_feeds(filename):
    """
    Alternativa direta: /static/feeds/... (útil para assets absolutos)
    """
    clean = filename.split('?')[0]
    if not allowed_file(clean):
        logger.warning("Extensão não permitida: %s", clean)
        abort(404)

    base_dir = get_base_dir("feeds/dist")
    resp, not_found = _safe_send(base_dir, clean)
    if not_found:
        abort(404)
    return resp


@bp.get("/api/static/feeds/<path:filename>")
def api_static_feeds(filename):
    """
    Serve arquivos de feeds via API (com CORS)
    """
    clean = filename.split('?')[0]
    if not allowed_file(clean):
        return jsonify({"error": "File type not allowed"}), 404

    base_dir = get_base_dir("feeds/dist")
    resp, not_found = _safe_send(base_dir, clean)
    if not_found:
        return jsonify({"error": "File not found"}), 404
    return resp


@bp.get("/api/feeds/files/list")
def list_feeds_files():
    """
    Lista arquivos disponíveis em static/feeds/dist (debug)
    """
    base_dir = get_base_dir("feeds/dist")
    if not os.path.exists(base_dir):
        return jsonify({
            "error": "Directory not found",
            "base_dir": base_dir,
            "cwd": os.getcwd()
        }), 404

    files = []
    for name in os.listdir(base_dir):
        path = os.path.join(base_dir, name)
        if os.path.isfile(path):
            files.append({
                "name": name,
                "size": os.path.getsize(path),
                "allowed": allowed_file(name),
                "urls": {
                    "feeds": f"/feeds/{name}",
                    "static": f"/static/feeds/{name}",
                    "api": f"/api/static/feeds/{name}"
                }
            })

    return jsonify({
        "base_dir": base_dir,
        "cwd": os.getcwd(),
        "total_files": len(files),
        "files": sorted(files, key=lambda x: x["name"])
    }), 200


@bp.get("/api/feeds/files/test")
def test_feeds_routes():
    """
    Testa as rotas de FEEDS (similar ao /api/files/test)
    """
    base_dir = get_base_dir("feeds/dist")
    results = {
        "base_directory": base_dir,
        "cwd": os.getcwd(),
        "directory_exists": os.path.exists(base_dir),
        "routes": {
            "/feeds": "SPA index.html",
            "/feeds/<filename>": "Assets do build com fallback SPA",
            "/static/feeds/<filename>": "Serve direto arquivos estáticos",
            "/api/static/feeds/<filename>": "Serve via API",
            "/api/feeds/files/list": "Lista arquivos disponíveis",
            "/api/feeds/files/test": "Testa as rotas"
        },
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "available_files": []
    }

    if os.path.exists(base_dir):
        for name in os.listdir(base_dir):
            p = os.path.join(base_dir, name)
            if os.path.isfile(p):
                results["available_files"].append({
                    "name": name,
                    "size_bytes": os.path.getsize(p),
                    "allowed": allowed_file(name),
                    "urls": {
                        "feeds": f"/feeds/{name}",
                        "static": f"/static/feeds/{name}",
                        "api": f"/api/static/feeds/{name}"
                    }
                })
    return jsonify(results), 200


# ======================================================================
# INSTAGRAM (mantidos do seu arquivo original)  ------------------------
# ======================================================================

@bp.get("/static/instagram/<path:filename>")
def serve_static_instagram(filename):
    """
    Serve arquivos estáticos da pasta static/instagram
    Usa: /static/instagram/index.html ou /static/instagram/core-service-p-boot.json?v=123
    """
    clean_filename = filename.split('?')[0]
    logger.info("Servindo arquivo estático: %s (original: %s)", clean_filename, filename)

    if not allowed_file(clean_filename):
        logger.warning("Extensão não permitida: %s", clean_filename)
        abort(404)

    try:
        base_dir = get_base_dir("instagram")
        resp, not_found = _safe_send(base_dir, clean_filename)
        if not_found:
            abort(404)
        return resp
    except Exception as e:
        logger.error("Erro ao servir arquivo estático: %s", e, exc_info=True)
        abort(500)


@bp.get("/api/static/instagram/<path:filename>")
def serve_via_api(filename):
    """
    Alternativa: Serve arquivos via /api/static/instagram/...
    Usa: /api/static/instagram/core-service-p-boot.json
    """
    clean_filename = filename.split('?')[0]
    logger.info("Servindo via API: %s", clean_filename)

    if not allowed_file(clean_filename):
        logger.warning("Extensão não permitida: %s", clean_filename)
        return jsonify({"error": "File type not allowed"}), 404

    try:
        base_dir = get_base_dir("instagram")
        resp, not_found = _safe_send(base_dir, clean_filename)
        if not_found:
            return jsonify({"error": "File not found"}), 404
        return resp
    except Exception as e:
        logger.error("Erro ao servir arquivo via API: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.get("/api/mock/posts")
def mock_posts():
    """
    Endpoint para servir dados mockados de posts para testes
    Usa: /api/mock/posts
    """
    logger.info("Servindo dados mockados")
    try:
        base_dir = get_base_dir("instagram")
        json_file = os.path.join(base_dir, "mock_posts.json")

        if not os.path.exists(json_file):
            logger.warning("Arquivo mock não encontrado: %s", json_file)
            return jsonify({"code": 200, "payload": []}), 200

        logger.info("Enviando mock posts: %s", json_file)
        resp, not_found = _safe_send(base_dir, "mock_posts.json")
        if not_found:
            return jsonify({"code": 404, "error": "mock_posts.json not found"}), 404
        return resp
    except Exception as e:
        logger.error("Erro ao servir mock posts: %s", e, exc_info=True)
        return jsonify({"code": 500, "error": str(e)}), 500


@bp.get("/api/mock/boot")
def mock_boot():
    """
    Endpoint para servir dados de boot mockados
    Usa: /api/mock/boot
    """
    logger.info("Servindo dados de boot")
    try:
        base_dir = get_base_dir("instagram")
        json_file = os.path.join(base_dir, "core-service-p-boot.json")

        if not os.path.exists(json_file):
            logger.warning("Arquivo boot não encontrado: %s", json_file)
            return jsonify({"code": 200, "payload": {"initialized": True}}), 200

        logger.info("Enviando boot data: %s", json_file)
        resp, not_found = _safe_send(base_dir, "core-service-p-boot.json")
        if not_found:
            return jsonify({"code": 404, "error": "core-service-p-boot.json not found"}), 404
        return resp
    except Exception as e:
        logger.error("Erro ao servir boot data: %s", e, exc_info=True)
        return jsonify({"code": 500, "error": str(e)}), 500


@bp.get("/api/files/list")
def list_files():
    """
    Endpoint para listar arquivos disponíveis (DEBUG) de static/instagram
    Usa: /api/files/list
    """
    logger.info("Listando arquivos disponíveis")
    try:
        base_dir = get_base_dir("instagram")

        if not os.path.exists(base_dir):
            logger.warning("Diretório não existe: %s", base_dir)
            return jsonify({
                "error": "Directory not found",
                "base_dir": base_dir,
                "cwd": os.getcwd()
            }), 404

        files = []
        for filename in os.listdir(base_dir):
            filepath = os.path.join(base_dir, filename)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                files.append({
                    "name": filename,
                    "size": size,
                    "allowed": allowed_file(filename),
                    "urls": {
                        "static": f"/static/instagram/{filename}",
                        "api": f"/api/static/instagram/{filename}",
                        "with_cache_bust": f"/static/instagram/{filename}?v=123"
                    }
                })

        logger.info("Total de arquivos: %d", len(files))
        return jsonify({
            "base_dir": base_dir,
            "cwd": os.getcwd(),
            "total_files": len(files),
            "files": sorted(files, key=lambda x: x['name'])
        }), 200
    except Exception as e:
        logger.error("Erro ao listar arquivos: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.get("/api/files/test")
def test_routes():
    """
    Endpoint para testar as rotas de arquivos estáticos (instagram)
    Usa: /api/files/test
    """
    logger.info("Testando rotas de arquivos estáticos")

    base_dir = get_base_dir("instagram")

    results = {
        "base_directory": base_dir,
        "cwd": os.getcwd(),
        "directory_exists": os.path.exists(base_dir),
        "possible_paths": {
            "/app/static/instagram": os.path.exists("/app/static/instagram"),
            "/static/instagram": os.path.exists("/static/instagram"),
            "/app/src/static/instagram": os.path.exists("/app/src/static/instagram"),
            "static/instagram": os.path.exists("static/instagram"),
            "src/app/static/instagram": os.path.exists("src/app/static/instagram"),
            "./static/instagram": os.path.exists("./static/instagram"),
        },
        "routes": {
            "/static/instagram/<filename>": "Serve arquivos estáticos (suporta cache busting com ?v=)",
            "/api/static/instagram/<filename>": "Serve via API",
            "/api/mock/posts": "Serve mock_posts.json",
            "/api/mock/boot": "Serve core-service-p-boot.json",
            "/api/files/list": "Lista arquivos disponíveis",
            "/api/files/test": "Testa as rotas"
        },
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "available_files": [],
        "test_urls": {
            "index.html": "/static/instagram/index.html",
            "mock_posts.json": "/static/instagram/mock_posts.json",
            "core-service-p-boot.json": "/static/instagram/core-service-p-boot.json?v=123"
        }
    }

    # Listar arquivos disponíveis
    if os.path.exists(base_dir):
        try:
            for filename in os.listdir(base_dir):
                filepath = os.path.join(base_dir, filename)
                if os.path.isfile(filepath):
                    results["available_files"].append({
                        "name": filename,
                        "size_bytes": os.path.getsize(filepath),
                        "allowed": allowed_file(filename),
                        "urls": {
                            "static": f"/static/instagram/{filename}",
                            "api": f"/api/static/instagram/{filename}",
                            "with_cache_bust": f"/static/instagram/{filename}?v=123"
                        }
                    })
        except Exception as e:
            results["error_listing_files"] = str(e)
            logger.error("Erro ao listar arquivos para teste: %s", e)

    return jsonify(results), 200
