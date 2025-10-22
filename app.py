import os
import time
import math
import mimetypes
import argparse
import requests
from flask import Flask, jsonify, request, Response, send_from_directory, abort, make_response
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()
app = Flask(__name__, static_folder='static')
CORS(app)

# =========================
# Config
# =========================
ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
USER_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
GRAPH_API_URL = 'https://graph.instagram.com/v22.0'

CACHE_DURATION_SECONDS = int(os.getenv('CACHE_DURATION_SECONDS', '3600'))  # posts (1h)
PLACE_ID = os.getenv('GOOGLE_PLACE_ID')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

MEDIA_CACHE_DIR = os.getenv('MEDIA_CACHE_DIR', os.path.join(os.getcwd(), 'cache', 'instagram'))
MEDIA_CACHE_TTL_SECONDS = int(os.getenv('MEDIA_CACHE_TTL_SECONDS', '3600'))  # mídias (1h)
MEDIA_CACHE_MAX_BYTES = int(os.getenv('MEDIA_CACHE_MAX_BYTES', str(25 * 1024 * 1024)))  # 25MB
WARMUP_TOKEN = os.getenv('WARMUP_TOKEN', '')
WARMUP_SLEEP_SECONDS = float(os.getenv('WARMUP_SLEEP_SECONDS', '0.25'))

os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

# Cache simples com TTL (em memória) para respostas JSON
api_cache = {}  # key -> {"data": ..., "ts": epoch}


# =========================
# Utils de cache em memória
# =========================
def get_from_cache(key):
    item = api_cache.get(key)
    if not item:
        return None
    if (time.time() - item["ts"]) > CACHE_DURATION_SECONDS:
        api_cache.pop(key, None)
        return None
    return item["data"]


def set_in_cache(key, data):
    api_cache[key] = {"data": data, "ts": time.time()}


# =========================
# Instagram helpers
# =========================
def ig_get(path_or_id: str, fields: str, extra: dict | None = None):
    """GET na Graph API com token e timeout padrão; aceita params extras (ex.: limit, after)."""
    url = f"{GRAPH_API_URL.rstrip('/')}/{path_or_id.lstrip('/')}"
    params = {"fields": fields, "access_token": ACCESS_TOKEN}
    if extra:
        params.update(extra)
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def ig_get_url(full_url: str):
    """GET em uma URL 'next' da Graph (já com token embutido)."""
    r = requests.get(full_url, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_user_profile():
    cache_key = f"profile_{USER_ID}"
    cached = get_from_cache(cache_key)
    if cached:
        return cached

    fields = "id,username,biography,followers_count,follows_count,media_count,account_type"
    data = ig_get("me", fields)

    payload = {
        "username": data.get("username"),
        "profilePictureUrl": None,  # Graph IG nem sempre fornece
        "fullName": None,
        "isVerified": True,  # ajuste conforme sua regra
        "biography": data.get("biography"),
        "postsCount": data.get("media_count"),
        "followersCount": data.get("followers_count"),
        "followingCount": data.get("follows_count"),
    }
    set_in_cache(cache_key, payload)
    return payload


# =========================
# Cache de mídia em DISCO (por media_id)
# =========================
def _ext_from_content_type(ct: str) -> str:
    if not ct:
        return ''
    if 'jpeg' in ct:
        return '.jpg'
    if 'png' in ct:
        return '.png'
    if 'gif' in ct:
        return '.gif'
    if 'webp' in ct:
        return '.webp'
    if 'mp4' in ct:
        return '.mp4'
    if 'mpeg' in ct:
        return '.mpg'
    return mimetypes.guess_extension(ct) or ''


def _cache_paths(media_id: str, content_type: str = None):
    """Retorna caminho do arquivo e do .meta (content-type)."""
    for name in os.listdir(MEDIA_CACHE_DIR):
        if name.startswith(media_id + "."):
            p = os.path.join(MEDIA_CACHE_DIR, name)
            meta = os.path.join(MEDIA_CACHE_DIR, f"{media_id}.meta")
            return p, meta
    ext = _ext_from_content_type(content_type) if content_type else '.bin'
    file_path = os.path.join(MEDIA_CACHE_DIR, f"{media_id}{ext}")
    meta_path = os.path.join(MEDIA_CACHE_DIR, f"{media_id}.meta")
    return file_path, meta_path


def _write_meta(meta_path: str, content_type: str):
    try:
        with open(meta_path, 'w') as f:
            f.write(content_type or 'application/octet-stream')
    except Exception:
        pass


def _read_meta(meta_path: str) -> str:
    try:
        with open(meta_path, 'r') as f:
            return f.read().strip()
    except Exception:
        return 'application/octet-stream'


def _is_cache_fresh(file_path: str) -> bool:
    if not os.path.exists(file_path):
        return False
    age = time.time() - os.path.getmtime(file_path)
    return age <= MEDIA_CACHE_TTL_SECONDS


def _save_stream_to_file(resp: requests.Response, dst_path: str, max_bytes: int) -> str:
    """Salva stream respeitando um limite de bytes. Retorna caminho usado (ou '' se abortar)."""
    tmp_path = dst_path + ".tmp"
    total = 0
    with open(tmp_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=1024 * 64):
            if chunk:
                total += len(chunk)
                if total > max_bytes:
                    f.close()
                    os.remove(tmp_path)
                    return ''
                f.write(chunk)
    if os.path.exists(dst_path):
        os.remove(dst_path)
    os.rename(tmp_path, dst_path)
    return dst_path


def drop_media_cache(media_id: str):
    """Remove arquivos de cache (mídia + meta) de um media_id."""
    for name in os.listdir(MEDIA_CACHE_DIR):
        if name.startswith(media_id + "."):
            try:
                os.remove(os.path.join(MEDIA_CACHE_DIR, name))
            except Exception:
                pass


def ensure_media_cached(media_id: str) -> tuple[str, str]:
    """
    Garante mídia em cache; retorna (file_path, content_type).
    Se arquivo fresco já existir, usa. Senão busca via Graph, baixa e salva.
    Pode não salvar se exceder MEDIA_CACHE_MAX_BYTES; nesse caso retorna ('','').
    """
    existing_file, existing_meta = _cache_paths(media_id)
    if os.path.exists(existing_file) and _is_cache_fresh(existing_file):
        return existing_file, _read_meta(existing_meta)

    info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
    src = info.get("media_url") or info.get("thumbnail_url")
    if not src:
        return '', ''

    with requests.get(src, stream=True, timeout=20) as cdn:
        cdn.raise_for_status()
        ct = cdn.headers.get('Content-Type', 'application/octet-stream')
        file_path, meta_path = _cache_paths(media_id, ct)
        saved_path = _save_stream_to_file(cdn, file_path, MEDIA_CACHE_MAX_BYTES)
    if saved_path:
        _write_meta(meta_path, ct)
        os.utime(saved_path, None)
        return saved_path, ct
    return '', ''  # muito grande → não cacheado


# =========================
# Servir arquivo com suporte a Range (206)
# =========================
def serve_file_with_range(path: str, content_type: str):
    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range', None)

    if not range_header:
        resp = make_response()
        with open(path, 'rb') as f:
            resp.data = f.read()
        resp.headers['Content-Type'] = content_type
        resp.headers['Content-Length'] = str(file_size)
        resp.headers['Accept-Ranges'] = 'bytes'
        return resp

    try:
        units, rng = range_header.split('=')
        if units != 'bytes':
            raise ValueError
        start_str, end_str = rng.split('-')
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start < 0:
            raise ValueError
    except Exception:
        return Response(status=416)

    length = end - start + 1
    with open(path, 'rb') as f:
        f.seek(start)
        chunk = f.read(length)

    resp = Response(chunk, status=206, mimetype=content_type)
    resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Content-Length'] = str(length)
    return resp


# =========================
# Rotas Instagram
# =========================
@app.route('/api/instagram/user_profile', methods=['GET'])
def get_user_profile_route():
    try:
        profile = fetch_user_profile()
        return jsonify({"code": 200, "payload": profile, "message": ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/instagram/media_proxy', methods=['GET'])
def media_proxy():
    """
    Proxy por media_id com cache em disco:
    - se arquivo fresco existir → serve do arquivo (com Range)
    - senão → baixa da CDN (via Graph), salva (se <= limite) e serve
    Forçar refresh: /api/instagram/media_proxy?id=<id>&refresh=1
    """
    media_id = request.args.get('id')
    if not media_id:
        return Response('Missing id', status=400)

    refresh = request.args.get('refresh') == '1'

    try:
        if not refresh:
            file_path, ct = ensure_media_cached(media_id)
            if file_path and os.path.exists(file_path):
                return serve_file_with_range(file_path, ct)

        # refresh forçado ou cache indisponível
        info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
        src = info.get("media_url") or info.get("thumbnail_url")
        if not src:
            return Response('No media_url available', status=502)

        with requests.get(src, stream=True, timeout=20) as cdn:
            cdn.raise_for_status()
            ct = cdn.headers.get('Content-Type', 'application/octet-stream')
            file_path, meta_path = _cache_paths(media_id, ct)
            saved_path = _save_stream_to_file(cdn, file_path, MEDIA_CACHE_MAX_BYTES)

        if saved_path:
            _write_meta(meta_path, ct)
            return serve_file_with_range(saved_path, ct)

        # fallback sem cache (muito grande)
        cdn2 = requests.get(src, stream=True, timeout=20)
        cdn2.raise_for_status()
        return Response(cdn2.iter_content(chunk_size=1024 * 64),
                        content_type=ct,
                        direct_passthrough=True)

    except requests.exceptions.RequestException as e:
        status = getattr(e.response, 'status_code', 500)
        return Response(f'Error: {e}', status=status)
    except Exception as e:
        return Response(f'Error: {e}', status=500)


@app.route('/api/instagram/posts', methods=['GET'])
def get_user_posts():
    """
    Retorna posts mantendo a estrutura antiga de media_items,
    mas substitui as URLs da CDN por URLs do backend:
      /api/instagram/media_proxy?id=<media_id>
    """
    username = request.args.get('username', 'me')
    cache_key = f"posts_{username}"
    cached = get_from_cache(cache_key)
    if cached:
        print(f"Servindo posts de '{username}' do cache (TTL {CACHE_DURATION_SECONDS}s)")
        return jsonify(cached)

    if not ACCESS_TOKEN:
        return jsonify({"error": "Access Token não configurado no backend"}), 500

    try:
        user_info = fetch_user_profile()
    except Exception as e:
        return jsonify({"error": "Falha ao buscar perfil: " + str(e)}), 500

    fields = "id,caption,media_type,permalink,timestamp,username,children{id,media_type},comments_count,like_count"
    try:
        api_data = ig_get(f"{USER_ID}/media", fields)
        formatted_posts = []

        width, height = 1080.0, 1920.0

        for post in api_data.get("data", []):
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

            def make_cover(mid: str):
                return {
                    "thumbnail": {
                        "url": f"/api/instagram/media_proxy?id={mid}",
                        "width": width,
                        "height": height
                    },
                    "standard": None,
                    "original": None
                }

            media_items = []
            ptype = (post.get("media_type") or "").upper()

            if ptype in ("IMAGE", "VIDEO"):
                mid = post.get("id")
                media_items.append({
                    "type": ptype.lower(),
                    "url": f"/api/instagram/media_proxy?id={mid}",
                    "cover": make_cover(mid),
                    "id": mid
                })
            elif ptype == "CAROUSEL_ALBUM":
                children = (post.get("children") or {}).get("data", [])
                for child in children:
                    ctype = (child.get("media_type") or "").upper()
                    mid = child.get("id")
                    media_items.append({
                        "type": ctype.lower(),
                        "url": f"/api/instagram/media_proxy?id={mid}",
                        "cover": make_cover(mid),
                        "id": mid
                    })

            formatted_post = {
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
            }
            formatted_posts.append(formatted_post)

        final_response = {"code": 200, "payload": formatted_posts}
        set_in_cache(cache_key, final_response)
        print(f"Posts de '{username}' buscados da API e cacheados (TTL {CACHE_DURATION_SECONDS}s)")
        return jsonify(final_response)

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar posts do Instagram: {e}")
        error_payload = {"error": str(e)}
        if e.response is not None:
            try:
                error_payload["details"] = e.response.json()
            except ValueError:
                error_payload["details"] = e.response.text
        return jsonify(error_payload), getattr(e.response, 'status_code', 500)


# =========================
# WARM-UP (endpoint + helpers)
# =========================
def collect_media_ids(limit_posts: int = 20) -> list[str]:
    """Coleta media_ids dos últimos posts (inclui filhos de carrossel) até atingir limit_posts."""
    ids: list[str] = []
    got_posts = 0
    fields = "id,media_type,children{id,media_type}"
    url = f"{GRAPH_API_URL}/{USER_ID}/media?fields={fields}&limit=25&access_token={ACCESS_TOKEN}"

    try:
        while url and got_posts < limit_posts:
            data = ig_get_url(url)
            for post in data.get("data", []):
                if got_posts >= limit_posts:
                    break
                ptype = (post.get("media_type") or "").upper()
                if ptype in ("IMAGE", "VIDEO"):
                    ids.append(post.get("id"))
                elif ptype == "CAROUSEL_ALBUM":
                    for child in (post.get("children") or {}).get("data", []):
                        ids.append(child.get("id"))
                got_posts += 1

            url = (data.get("paging") or {}).get("next")
    except requests.exceptions.RequestException:
        pass

    # Dedup
    seen = set()
    unique_ids = []
    for mid in ids:
        if mid and mid not in seen:
            seen.add(mid)
            unique_ids.append(mid)
    return unique_ids


def warmup(limit_posts: int = 20, force: bool = False) -> dict:
    mids = collect_media_ids(limit_posts)
    ok, skipped, failed = 0, 0, 0
    details = []

    for mid in mids:
        try:
            if force:
                drop_media_cache(mid)
            file_path, ct = ensure_media_cached(mid)
            if file_path:
                ok += 1
                details.append({"id": mid, "status": "cached", "path": file_path})
            else:
                skipped += 1
                details.append({"id": mid, "status": "skipped"})
        except Exception as e:
            failed += 1
            details.append({"id": mid, "status": "failed", "error": str(e)})
        time.sleep(WARMUP_SLEEP_SECONDS)

    return {"posts_scanned": limit_posts, "media_found": len(mids), "cached": ok, "skipped": skipped, "failed": failed,
            "details": details}


def _is_local_request() -> bool:
    # Atrás do Nginx, prefira token; mas se não houver token, permita apenas localhost
    remote = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
    return remote.startswith('127.0.0.1') or remote.startswith('::1')


@app.route('/api/instagram/warmup', methods=['POST'])
def warmup_route():
    token = request.headers.get('X-Warmup-Token') or request.args.get('token', '')
    if WARMUP_TOKEN:
        if token != WARMUP_TOKEN:
            return jsonify({"error": "unauthorized"}), 401
    else:
        if not _is_local_request():
            return jsonify({"error": "forbidden"}), 403

    try:
        limit_posts = int(request.args.get('limit', '20'))
        force = request.args.get('force') == '1' or request.json.get('force') if request.is_json else False
    except Exception:
        limit_posts = 20
        force = False

    result = warmup(limit_posts=limit_posts, force=bool(force))
    return jsonify({"code": 200, "payload": result})


# =========================
# Legacy proxy por URL direta (se ainda usar em algum lugar)
# =========================
@app.route('/api/instagram/proxy-image', methods=['GET'])
def proxy_image_legacy():
    url = request.args.get('url')
    if not url:
        return Response('Missing URL', status=400)
    if not (url.startswith('https://scontent') or url.startswith('https://instagram')):
        return Response('Blocked domain', status=403)
    try:
        r = requests.get(url, stream=True, timeout=8)
        r.raise_for_status()
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        return Response(r.content, content_type=content_type)
    except Exception as e:
        return Response(f'Error: {e}', status=500)


# =========================
# Google Reviews
# =========================
@app.route('/api/google/reviews')
def google_reviews():
    try:
        reviews = get_google_reviews()
        return jsonify({"code": 200, "payload": reviews})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)})


def get_google_reviews():
    if not PLACE_ID or not GOOGLE_API_KEY:
        return []
    url = (
        "https://maps.googleapis.com/maps/api/place/details/json"
        f"?place_id={PLACE_ID}"
        f"&fields=reviews,rating,user_ratings_total,name"
        f"&key={GOOGLE_API_KEY}"
    )
    response = requests.get(url, timeout=10)
    data = response.json()
    if "result" in data and "reviews" in data["result"]:
        return data["result"]["reviews"]
    else:
        return []


# =========================
# Static
# =========================
ALLOWED_EXTENSIONS = {'.json', '.js', '.html', '.css', '.jpg', '.png'}

def allowed_file(filename):
    ext = os.path.splitext(filename)[1]
    return ext in ALLOWED_EXTENSIONS


@app.route('/api/config')
def get_config():
    """Retorna configurações para o frontend."""
    return jsonify({
        "code": 200,
        "payload": {
            "apiBaseUrl": API_BASE_URL
        }
    })


@app.route('/health')
def health():
    return jsonify({"code": 200, "payload": "OK"})

@app.route('/static/instagram/<path:filename>')
def serve_static_instagram(filename):
    if not allowed_file(filename):
        abort(404)
    return send_from_directory('static/instagram', filename)


# =========================
# Main / CLI
# =========================
def cli_warmup(limit: int, force: bool):
    result = warmup(limit_posts=limit, force=force)
    print(
        f"WARMUP => posts_scanned={result['posts_scanned']} media_found={result['media_found']} cached={result['cached']} skipped={result['skipped']} failed={result['failed']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="API Instagram com cache e warm-up")
    parser.add_argument('--warmup', action='store_true', help='Executa warm-up e sai')
    parser.add_argument('--limit', type=int, default=20, help='Quantidade de posts para varrer no warm-up')
    parser.add_argument('--force', action='store_true', help='Força recachear as mídias')
    parser.add_argument('--port', type=int, default=8080, help='Porta do servidor Flask (dev)')
    args = parser.parse_args()

    if args.warmup:
        cli_warmup(limit=args.limit, force=args.force)
    else:
        app.run(debug=True, port=args.port)
