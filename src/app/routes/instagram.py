from flask import Blueprint, jsonify, request, current_app, Response
from ..services.instagram import fetch_user_profile, ig_get
from ..services.cache import get_from_cache, set_in_cache, clear_memory_cache
from ..services.media_cache import ensure_media_cached, serve_file_with_range, clear_media_cache_all
from ..services.warmup import warmup
import logging

logger = logging.getLogger(__name__)

bp = Blueprint("instagram", __name__)


@bp.get("/config")
def get_config():
    return jsonify({"code": 200, "payload": {"apiBaseUrl": current_app.config["API_BASE_URL"]}})


@bp.get("/user_profile")
def user_profile():
    try:
        profile = fetch_user_profile()
        return jsonify({"code": 200, "payload": profile})
    except Exception as e:
        logger.error(f"Erro ao buscar perfil: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.get("/media_proxy")
def media_proxy():
    media_id = request.args.get('id')
    if not media_id:
        return Response('Missing id', status=400)

    logger.info(f"media_proxy chamado: id={media_id}")

    refresh = request.args.get('refresh') == '1'
    prefer_thumb = request.args.get('thumb') == '1'
    variant = 'thumb' if prefer_thumb else 'media'

    try:
        # Se não é refresh, tenta usar cache
        if not refresh:
            file_path, ct = ensure_media_cached(media_id, variant=variant)
            if file_path:
                logger.info(f"Servindo do cache: {file_path}")
                return serve_file_with_range(file_path, ct)
            else:
                logger.info(f"Cache não disponível ou expirado para {media_id}")

        # Busca informações do Instagram
        logger.info(f"Buscando informações do Instagram para {media_id}")
        info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
        logger.info(f"Info recebida: {info}")

        # Decide qual URL usar
        if prefer_thumb:
            src = info.get("thumbnail_url") or info.get("media_url")
        else:
            src = info.get("media_url") or info.get("thumbnail_url")

        if not src:
            logger.error(f"Nenhuma URL disponível para {media_id}: {info}")
            return Response('No media_url available', status=502)

        logger.info(f"URL selecionada: {src[:80]}...")

        # Faz cache e serve
        file_path, ct = ensure_media_cached(media_id, variant=variant, explicit_src=src)
        if file_path:
            logger.info(f"Mídia cacheada e sendo servida: {file_path}")
            return serve_file_with_range(file_path, ct)
        else:
            logger.error(f"Falha ao cachear mídia: {media_id}")
            return Response('Unable to cache media', status=502)
    except Exception as e:
        logger.error(f"Erro no media_proxy: {e}", exc_info=True)
        return Response(f'Error: {e}', status=500)


@bp.get("/posts")
def posts():
    username = request.args.get('username', 'me')
    ttl = current_app.config['CACHE_DURATION_SECONDS']
    api_base = current_app.config['API_BASE_URL'].rstrip('/')

    logger.info(f"posts chamado: username={username}")

    def build_proxy_url(path: str) -> str:
        # garante que sempre geramos URLs absolutas para o widget
        from urllib.parse import urljoin
        rel = path.lstrip('/')
        return urljoin(f"{api_base}/", rel)

    cache_key = f"posts_{username}"
    cached = get_from_cache(cache_key, ttl)
    if cached:
        logger.info(f"Retornando posts do cache: {cache_key}")
        return jsonify(cached)

    if not current_app.config['ACCESS_TOKEN']:
        logger.error("Access Token não configurado")
        return jsonify({"error": "Access Token não configurado no backend"}), 500

    try:
        logger.info(f"Buscando perfil do usuário")
        user_info = fetch_user_profile()

        logger.info(f"Buscando posts do usuário {current_app.config['USER_ID']}")
        fields = "id,caption,media_type,permalink,timestamp,username,children{id,media_type},comments_count,like_count"
        api_data = ig_get(f"{current_app.config['USER_ID']}/media", fields)

        logger.info(f"Posts recebidos: {len(api_data.get('data', []))}")

        width, height = 1080.0, 1920.0

        def make_cover(mid: str):
            thumb_path = f"/api/instagram/media_proxy?id={mid}&thumb=1"
            return {
                "thumbnail": {
                    "url": build_proxy_url(thumb_path),
                    "width": width, "height": height
                },
                "standard": None, "original": None
            }

        formatted = []
        for post in api_data.get("data", []):
            ptype = (post.get("media_type") or "").upper()
            media_items = []

            if ptype in ("IMAGE", "VIDEO"):
                mid = post.get("id")
                media_items.append({
                    "type": ptype.lower(),
                    "url": build_proxy_url(f"/api/instagram/media_proxy?id={mid}"),
                    "cover": make_cover(mid),
                    "id": mid
                })
            elif ptype == "CAROUSEL_ALBUM":
                for child in (post.get("children") or {}).get("data", []):
                    ctype = (child.get("media_type") or "").upper()
                    mid = child.get("id")
                    media_items.append({
                        "type": ctype.lower(),
                        "url": build_proxy_url(f"/api/instagram/media_proxy?id={mid}"),
                        "cover": make_cover(mid),
                        "id": mid
                    })

            author = {
                "username": user_info.get("username"),
                "url": None,
                "profilePictureUrl": user_info.get("profilePictureUrl"),
                "isVerifiedProfile": user_info.get("isVerified"),
                "name": user_info.get("fullName"),
                "biography": user_info.get("biography"),
                "postsCount": user_info.get("postsCount"),
                "followersCount": user_info.get("followersCount"),
                "followingCount": user_info.get("followingCount")
            }

            formatted.append({
                "vendorId": post.get("id"),
                "type": (post.get("media_type") or "").lower().replace("_album", ""),
                "link": post.get("permalink"),
                "publishedAt": post.get("timestamp"),
                "author": author,
                "media": media_items,
                "comments": [],
                "caption": post.get("caption"),
                "commentsCount": post.get("comments_count", 0),
                "likesCount": post.get("like_count", 0),
                "extra": {"platform": "instagram"},
                "isPinned": None
            })

        final_resp = {"code": 200, "payload": formatted}
        set_in_cache(cache_key, final_resp)
        logger.info(f"Posts formatados e cacheados: {len(formatted)}")
        return jsonify(final_resp)
    except Exception as e:
        logger.error(f"Erro ao buscar posts: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.post("/warmup")
def warmup_route():
    token = (request.headers.get('X-Warmup-Token') or request.args.get('token', '') or '')
    cfg = current_app.config

    logger.info(f"warmup chamado")

    if cfg.get('WARMUP_TOKEN'):
        if token != cfg['WARMUP_TOKEN']:
            logger.warning("Warmup: token inválido")
            return jsonify({"error": "unauthorized"}), 401
    else:
        remote = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
        if not (remote.startswith('127.0.0.1') or remote.startswith('::1')):
            logger.warning(f"Warmup: acesso negado de {remote}")
            return jsonify({"error": "forbidden"}), 403

    try:
        limit_posts = int(request.args.get('limit', '20'))
        force = (request.args.get('force') == '1' or (request.is_json and (request.json or {}).get('force')))
    except Exception:
        limit_posts, force = 20, False

    logger.info(f"Iniciando warmup: limit={limit_posts}, force={force}")
    result = warmup(limit_posts=limit_posts, force=bool(force))
    return jsonify({"code": 200, "payload": result})


@bp.post("/admin/clear_cache")
def clear_cache_route():
    cfg = current_app.config

    # Auth simples por header (mesmo token do warmup)
    token = request.headers.get('X-Warmup-Token') or request.args.get('token', '')

    logger.info(f"clear_cache chamado")

    if cfg.get('WARMUP_TOKEN'):
        if token != cfg['WARMUP_TOKEN']:
            logger.warning("clear_cache: token inválido")
            return jsonify({"error": "unauthorized"}), 401
    else:
        # opcional: restringe a localhost se não houver token configurado
        remote = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
        if not (remote.startswith('127.') or remote == '::1'):
            logger.warning(f"clear_cache: acesso negado de {remote}")
            return jsonify({"error": "forbidden"}), 403

    body = request.get_json(silent=True) or {}
    what = (request.args.get('what') or body.get('what') or 'all').lower()
    media_id = (request.args.get('media_id') or body.get('media_id') or '').strip()

    result = {}

    if what in ('all', 'memory'):
        clear_memory_cache()
        result['memory'] = 'cleared'
        logger.info("Cache de memória limpo")

    if what in ('all', 'media'):
        # limpar tudo da pasta de mídia
        result['media'] = clear_media_cache_all()
        logger.info(f"Cache de mídia limpo: {result['media']}")

    if what == 'media_id':
        if not media_id:
            logger.error("clear_cache: media_id ausente")
            return jsonify({"error": "missing media_id"}), 400
        # remove apenas arquivos do media_id (mídia + .meta)
        from ..services.media_cache import drop_media_cache
        drop_media_cache(media_id)
        result['media_id'] = {"id": media_id, "status": "cleared"}
        logger.info(f"Cache de mídia específica limpo: {media_id}")

    if not result:
        logger.error("clear_cache: 'what' inválido")
        return jsonify({"error": "invalid 'what' (use all|memory|media|media_id)"}), 400

    return jsonify({"code": 200, "payload": result})