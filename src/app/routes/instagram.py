from flask import Blueprint, jsonify, request, current_app, Response
from ..services.instagram import fetch_user_profile, ig_get
from ..services.cache import get_from_cache, set_in_cache
from ..services.media_cache import ensure_media_cached, serve_file_with_range
from ..services.warmup import warmup

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
        return jsonify({"error": str(e)}), 500

@bp.get("/media_proxy")
def media_proxy():
    media_id = request.args.get('id')
    if not media_id: return Response('Missing id', status=400)
    refresh = request.args.get('refresh') == '1'
    try:
        if not refresh:
            file_path, ct = ensure_media_cached(media_id)
            if file_path: return serve_file_with_range(file_path, ct)
        info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
        src = info.get("media_url") or info.get("thumbnail_url")
        if not src: return Response('No media_url available', status=502)
        # força baixar e servir com cache fresco
        file_path, ct = ensure_media_cached(media_id)
        if file_path: return serve_file_with_range(file_path, ct)
        return Response('Unable to cache media', status=502)
    except Exception as e:
        return Response(f'Error: {e}', status=500)

@bp.get("/posts")
def posts():
    username = request.args.get('username', 'me')
    ttl = current_app.config['CACHE_DURATION_SECONDS']
    cache_key = f"posts_{username}"
    cached = get_from_cache(cache_key, ttl)
    if cached: return jsonify(cached)

    if not current_app.config['ACCESS_TOKEN']:
        return jsonify({"error": "Access Token não configurado no backend"}), 500

    try:
        user_info = fetch_user_profile()
        fields = "id,caption,media_type,permalink,timestamp,username,children{id,media_type},comments_count,like_count"
        api_data = ig_get(f"{current_app.config['USER_ID']}/media", fields)
        width, height = 1080.0, 1920.0
        def make_cover(mid: str):
            return {"thumbnail": {"url": f"/api/instagram/media_proxy?id={mid}", "width": width, "height": height}, "standard": None, "original": None}
        formatted = []
        for post in api_data.get("data", []):
            ptype = (post.get("media_type") or "").upper()
            media_items = []
            if ptype in ("IMAGE","VIDEO"):
                mid = post.get("id")
                media_items.append({"type": ptype.lower(), "url": f"/api/instagram/media_proxy?id={mid}", "cover": make_cover(mid), "id": mid})
            elif ptype == "CAROUSEL_ALBUM":
                for child in (post.get("children") or {}).get("data", []):
                    ctype = (child.get("media_type") or "").upper()
                    mid = child.get("id")
                    media_items.append({"type": ctype.lower(), "url": f"/api/instagram/media_proxy?id={mid}", "cover": make_cover(mid), "id": mid})

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
        return jsonify(final_resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/warmup")
def warmup_route():
    token = (request.headers.get('X-Warmup-Token') or request.args.get('token', '') or '')
    cfg = current_app.config
    if cfg['WARMUP_TOKEN']:
        if token != cfg['WARMUP_TOKEN']:
            return jsonify({"error": "unauthorized"}), 401
    else:
        remote = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
        if not (remote.startswith('127.0.0.1') or remote.startswith('::1')):
            return jsonify({"error": "forbidden"}), 403

    try:
        limit_posts = int(request.args.get('limit', '20'))
        force = (request.args.get('force') == '1' or (request.is_json and (request.json or {}).get('force')))
    except Exception:
        limit_posts, force = 20, False
    result = warmup(limit_posts=limit_posts, force=bool(force))
    return jsonify({"code": 200, "payload": result})
