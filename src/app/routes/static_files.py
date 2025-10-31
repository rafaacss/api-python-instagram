import os
import logging
import mimetypes
from flask import Blueprint, send_from_directory, abort, current_app, jsonify, make_response

logger = logging.getLogger(__name__)

bp = Blueprint("static_files", __name__)
ALLOWED_EXTENSIONS = {'.json', '.js', '.html', '.css', '.jpg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi'}


def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida"""
    # Remove query parameters (ex: ?v=123)
    filename = filename.split('?')[0]
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_base_dir():
    """
    Detecta automaticamente o diretório correto dos arquivos estáticos

    Tenta em ordem:
    1. /app/static/instagram (Docker com volume correto)
    2. /static/instagram (Docker com volume mapeado diretamente)
    3. /app/src/static/instagram (Docker com src)
    4. static/instagram (Local sem Docker)
    5. ./static/instagram (Local alternativo)
    """

    possible_paths = [
        "src/app/static/instagram",
        "/app/static/instagram",
        "/static/instagram",
        "/app/src/static/instagram",
        "static/instagram",
        "./static/instagram",
        os.path.join(os.getcwd(), "static/instagram"),
    ]

    logger.info(f"Procurando diretório estático em:")

    for path in possible_paths:
        abs_path = os.path.abspath(path)
        exists = os.path.exists(abs_path)
        logger.info(f"  - {abs_path} {'✓' if exists else '✗'}")

        if exists and os.path.isdir(abs_path):
            logger.info(f"✓ Usando: {abs_path}")
            return abs_path

    logger.warning(f"⚠ Nenhum diretório encontrado, usando padrão: {possible_paths[0]}")
    return os.path.abspath(possible_paths[0])


@bp.get("/static/instagram/<path:filename>")
def serve_static_instagram(filename):
    """
    Serve arquivos estáticos da pasta static/instagram
    Usa: /static/instagram/index.html ou /static/instagram/core-service-p-boot.json?v=123
    """
    # Remove query parameters do filename (ex: ?v=123)
    clean_filename = filename.split('?')[0]
    logger.info(f"Servindo arquivo estático: {clean_filename} (original: {filename})")

    if not allowed_file(clean_filename):
        logger.warning(f"Extensão não permitida: {clean_filename}")
        abort(404)

    try:
        base_dir = get_base_dir()

        # Validar path traversal
        requested_path = os.path.abspath(os.path.join(base_dir, clean_filename))
        if not requested_path.startswith(base_dir):
            logger.error(f"Tentativa de path traversal: {clean_filename}")
            abort(403)

        # Verificar se arquivo existe
        if not os.path.exists(requested_path):
            logger.warning(f"Arquivo não encontrado: {requested_path}")
            logger.info(f"Base dir: {base_dir}")
            if os.path.exists(base_dir):
                try:
                    files = os.listdir(base_dir)
                    logger.info(f"Arquivos disponíveis: {files}")
                except Exception as e:
                    logger.error(f"Erro ao listar: {e}")
                    abort(404)

        logger.info(f"Enviando: {requested_path}")
        print(send_from_directory(base_dir, clean_filename))
        # Usar send_from_directory
        response = make_response(send_from_directory(base_dir, clean_filename))

        # Adicionar headers apropriados
        if clean_filename.endswith('.json'):
            response.headers['Content-Type'] = 'application/json'
        elif clean_filename.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript'

        # Permitir cache (mas não abusar por causa do cache busting com ?v=)
        response.headers['Cache-Control'] = 'public, max-age=3600'
        response.headers['Access-Control-Allow-Origin'] = '*'

        return response
    except Exception as e:
        logger.error(f"Erro ao servir arquivo estático: {e}", exc_info=True)
        abort(500)


@bp.get("/api/static/instagram/<path:filename>")
def serve_via_api(filename):
    """
    Alternativa: Serve arquivos via /api/static/instagram/...
    Usa: /api/static/instagram/core-service-p-boot.json
    """
    clean_filename = filename.split('?')[0]
    logger.info(f"Servindo via API: {clean_filename}")

    if not allowed_file(clean_filename):
        logger.warning(f"Extensão não permitida: {clean_filename}")
        return jsonify({"error": "File type not allowed"}), 404

    try:
        base_dir = get_base_dir()

        requested_path = os.path.abspath(os.path.join(base_dir, clean_filename))
        if not requested_path.startswith(base_dir):
            logger.error(f"Tentativa de path traversal: {clean_filename}")
            return jsonify({"error": "Access denied"}), 403

        if not os.path.exists(requested_path):
            logger.warning(f"Arquivo não encontrado: {requested_path}")
            return jsonify({"error": "File not found"}), 404

        logger.info(f"Enviando via API: {requested_path}")
        response = make_response(send_from_directory(base_dir, clean_filename))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Erro ao servir arquivo via API: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.get("/api/mock/posts")
def mock_posts():
    """
    Endpoint para servir dados mockados de posts para testes
    Usa: /api/mock/posts
    """
    logger.info("Servindo dados mockados")
    try:
        base_dir = get_base_dir()
        json_file = os.path.join(base_dir, "mock_posts.json")

        if not os.path.exists(json_file):
            logger.warning(f"Arquivo mock não encontrado: {json_file}")
            return jsonify({"code": 200, "payload": []}), 200

        logger.info(f"Enviando mock posts: {json_file}")
        response = make_response(send_from_directory(base_dir, "mock_posts.json"))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Erro ao servir mock posts: {e}", exc_info=True)
        return jsonify({"code": 500, "error": str(e)}), 500


@bp.get("/api/mock/boot")
def mock_boot():
    """
    Endpoint para servir dados de boot mockados
    Usa: /api/mock/boot
    """
    logger.info("Servindo dados de boot")
    try:
        base_dir = get_base_dir()
        json_file = os.path.join(base_dir, "core-service-p-boot.json")

        if not os.path.exists(json_file):
            logger.warning(f"Arquivo boot não encontrado: {json_file}")
            return jsonify({"code": 200, "payload": {"initialized": True}}), 200

        logger.info(f"Enviando boot data: {json_file}")
        response = make_response(send_from_directory(base_dir, "core-service-p-boot.json"))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Erro ao servir boot data: {e}", exc_info=True)
        return jsonify({"code": 500, "error": str(e)}), 500


@bp.get("/api/files/list")
def list_files():
    """
    Endpoint para listar arquivos disponíveis (DEBUG)
    Usa: /api/files/list
    """
    logger.info("Listando arquivos disponíveis")
    try:
        base_dir = get_base_dir()

        if not os.path.exists(base_dir):
            logger.warning(f"Diretório não existe: {base_dir}")
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
                    "allowed": allowed_file(filename)
                })

        logger.info(f"Total de arquivos: {len(files)}")
        return jsonify({
            "base_dir": base_dir,
            "cwd": os.getcwd(),
            "total_files": len(files),
            "files": sorted(files, key=lambda x: x['name'])
        }), 200
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.get("/api/files/test")
def test_routes():
    """
    Endpoint para testar as rotas de arquivos estáticos
    Usa: /api/files/test
    """
    logger.info("Testando rotas de arquivos estáticos")

    base_dir = get_base_dir()

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
            logger.error(f"Erro ao listar arquivos para teste: {e}")

    return jsonify(results), 200