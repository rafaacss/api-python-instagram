from flask import Blueprint, jsonify, request, current_app, Response
from ..services.instagram import fetch_user_profile, ig_get
from ..services.cache import get_from_cache, set_in_cache, clear_memory_cache
from ..services.media_cache import ensure_media_cached, serve_file_with_range, clear_media_cache_all
from ..services.warmup import warmup
import logging
import re

logger = logging.getLogger(__name__)

bp = Blueprint("instagram", __name__)


# Função auxiliar para limpar e validar parâmetros
def clean_param(value, param_name="param"):
    """Remove caracteres inválidos dos parâmetros"""
    if not value:
        return None

    # Remove tudo após ':' (ex: "1:1" vira "1")
    value = str(value).split(':')[0].strip()

    # Remove caracteres não-alfanuméricos (exceto - e _)
    value = re.sub(r'[^a-zA-Z0-9\-_]', '', value)

    if not value:
        logger.warning(f"Parâmetro '{param_name}' ficou vazio após limpeza")
        return None

    logger.debug(f"Parâmetro '{param_name}' limpo: {value}")
    return value


def extract_images_from_media(media_items):
    """
    ✅ NOVO: Extrai images do array de media para compatibilidade com widget

    O widget JavaScript espera um array 'images' com as URLs das imagens.
    Este método extrai dos media items e retorna no formato esperado.

    Args:
        media_items: Array de media items com {type, url, cover, id}

    Returns:
        Array de imagens: [{url, width, height}, ...]

    Example:
        media_items = [
            {
                "type": "image",
                "url": "https://...",
                "cover": {...}
            }
        ]
        images = extract_images_from_media(media_items)
        # Result: [{"url": "https://...", "width": 1080, "height": 1920}]
    """
    images = []

    for media in media_items:
        try:
            # Tipo de media
            media_type = media.get("type", "").lower()

            # ✅ Para imagens
            if media_type == "image":
                # Preferir URL direta se disponível
                if media.get("url"):
                    images.append({
                        "url": media.get("url"),
                        "width": 1080,
                        "height": 1920
                    })
                    logger.debug(f"Imagem extraída (URL direta): {media.get('url')[:60]}")

                # Fallback para cover thumbnail
                elif media.get("cover", {}).get("thumbnail", {}).get("url"):
                    thumb = media["cover"]["thumbnail"]
                    images.append({
                        "url": thumb.get("url"),
                        "width": thumb.get("width", 1080),
                        "height": thumb.get("height", 1920)
                    })
                    logger.debug(f"Imagem extraída (cover): {thumb.get('url')[:60]}")

            # ✅ Para vídeos, usar thumbnail do cover
            elif media_type == "video":
                if media.get("cover", {}).get("thumbnail", {}).get("url"):
                    thumb = media["cover"]["thumbnail"]
                    images.append({
                        "url": thumb.get("url"),
                        "width": thumb.get("width", 1080),
                        "height": thumb.get("height", 1920)
                    })
                    logger.debug(f"Thumbnail de vídeo extraído: {thumb.get('url')[:60]}")

        except Exception as e:
            logger.warning(f"Erro ao extrair imagem de media: {e}")
            continue

    logger.info(f"Extraídas {len(images)} imagens de {len(media_items)} media items")
    return images


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
    # Limpar media_id (remove ":1" e caracteres inválidos)
    media_id = clean_param(request.args.get('id'), 'media_id')

    if not media_id:
        logger.warning(f"ID inválido recebido: {request.args.get('id')}")
        return Response('Missing or invalid id', status=400)

    logger.info(f"media_proxy chamado: id={media_id}")

    # Limpar parâmetros de refresh e thumb
    refresh_param = clean_param(request.args.get('refresh'), 'refresh')
    refresh = refresh_param == '1'

    thumb_param = clean_param(request.args.get('thumb'), 'thumb')
    prefer_thumb = thumb_param == '1'

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
        """
        Garante que sempre geramos URLs absolutas para o widget.
        Remove caracteres inválidos da URL.
        """
        from urllib.parse import urljoin, quote

        # Remove caracteres inválidos
        path = path.replace('\\', '/')

        # Remove múltiplos slashes
        while '//' in path:
            path = path.replace('//', '/')

        rel = path.lstrip('/')
        url = urljoin(f"{api_base}/", rel)

        logger.debug(f"URL construída: {url}")
        return url

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
            """Cria URL de thumbnail para a capa"""
            # Certificar que mid não tem caracteres inválidos
            mid_clean = clean_param(mid, 'media_id_cover')
            if not mid_clean:
                logger.warning(f"Media ID inválido para cover: {mid}")
                return {
                    "thumbnail": {
                        "url": "",
                        "width": width, "height": height
                    },
                    "standard": None, "original": None
                }

            thumb_path = f"/api/instagram/media_proxy?id={mid_clean}&thumb=1"
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
                # Limpar media ID
                mid_clean = clean_param(mid, 'post_media_id')
                if not mid_clean:
                    logger.warning(f"Pulando post com media_id inválido: {mid}")
                    continue

                media_items.append({
                    "type": ptype.lower(),
                    "url": build_proxy_url(f"/api/instagram/media_proxy?id={mid_clean}"),
                    "cover": make_cover(mid_clean),
                    "id": mid_clean
                })
            elif ptype == "CAROUSEL_ALBUM":
                for child in (post.get("children") or {}).get("data", []):
                    ctype = (child.get("media_type") or "").upper()
                    mid = child.get("id")

                    # Limpar media ID
                    mid_clean = clean_param(mid, 'carousel_media_id')
                    if not mid_clean:
                        logger.warning(f"Pulando item carousel com media_id inválido: {mid}")
                        continue

                    media_items.append({
                        "type": ctype.lower(),
                        "url": build_proxy_url(f"/api/instagram/media_proxy?id={mid_clean}"),
                        "cover": make_cover(mid_clean),
                        "id": mid_clean
                    })

            if not media_items:
                logger.warning(f"Post {post.get('id')} sem media items válidos")
                continue

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

            # ✅ NOVO: Extrair images do media para compatibilidade com widget
            images = extract_images_from_media(media_items)
            logger.info(f"Post {post.get('id')}: extraídas {len(images)} imagens de {len(media_items)} media items")

            formatted.append({
                "vendorId": post.get("id"),
                "type": (post.get("media_type") or "").lower().replace("_album", ""),
                "link": post.get("permalink"),
                "publishedAt": post.get("timestamp"),
                "author": author,
                "media": media_items,
                "images": images,
                "comments": [],
                "caption": post.get("caption"),
                "commentsCount": post.get("comments_count", 0),
                "likesCount": post.get("like_count", 0),
                "extra": {"platform": "instagram"},
                "isPinned": None
            })

        final_resp = {"code": 200, "payload": formatted}
        set_in_cache(cache_key, final_resp)
        logger.info(f"Posts formatados e cacheados: {len(formatted)} posts com images")
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

    # Limpar media_id
    media_id = clean_param(media_id, 'clear_cache_media_id') or ''

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
            logger.error("clear_cache: media_id ausente ou inválido")
            return jsonify({"error": "missing or invalid media_id"}), 400
        # remove apenas arquivos do media_id (mídia + .meta)
        from ..services.media_cache import drop_media_cache
        drop_media_cache(media_id)
        result['media_id'] = {"id": media_id, "status": "cleared"}
        logger.info(f"Cache de mídia específica limpo: {media_id}")

    if not result:
        logger.error("clear_cache: 'what' inválido")
        return jsonify({"error": "invalid 'what' (use all|memory|media|media_id)"}), 400

    return jsonify({"code": 200, "payload": result})