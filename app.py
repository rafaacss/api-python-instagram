import os
import time
import mimetypes
import argparse
import requests
from flask import Flask, jsonify, request, Response, send_from_directory, abort, make_response
from dotenv import load_dotenv
from flask_cors import CORS
from urllib.parse import urlparse, urljoin, parse_qs

# =========================================
# Bootstrap
# =========================================
load_dotenv()
app = Flask(__name__, static_folder='static')
CORS(app)

# =========================================
# Config
# =========================================
ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')  # Basic Display token
GRAPH_API_URL = 'https://graph.instagram.com/v22.0'

CACHE_DURATION_SECONDS = int(os.getenv('CACHE_DURATION_SECONDS', '3600'))  # JSON cache
MEDIA_CACHE_DIR = os.getenv('MEDIA_CACHE_DIR', '/tmp/instagram-cache')
MEDIA_CACHE_TTL_SECONDS = int(os.getenv('MEDIA_CACHE_TTL_SECONDS', '3600'))  # mídia
MEDIA_CACHE_MAX_BYTES = int(os.getenv('MEDIA_CACHE_MAX_BYTES', str(100 * 1024 * 1024)))  # 100MB
WARMUP_SLEEP_SECONDS = float(os.getenv('WARMUP_SLEEP_SECONDS', '0.25'))

os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)

# Cache em memória simples p/ JSON
api_cache: dict[str, dict] = {}  # key -> {"data": <obj>, "ts": epoch}

# PNG minúsculo como placeholder (quando algo falhar/undefined)
_TINY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x02\x00\x01'
    b'\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82'
)

def tiny_png_response(max_age=300):
    r = Response(_TINY_PNG, status=200, mimetype='image/png')
    r.headers['Cache-Control'] = f'public, max-age={max_age}'
    return r

# =========================================
# Helpers de cache JSON
# =========================================
def get_from_cache(key: str):
    item = api_cache.get(key)
    if not item:
        return None
    if (time.time() - item["ts"]) > CACHE_DURATION_SECONDS:
        api_cache.pop(key, None)
        return None
    return item["data"]

def set_in_cache(key: str, data):
    api_cache[key] = {"data": data, "ts": time.time()}

# =========================================
# Helpers de mídia/cache em disco
# =========================================
def _ext_from_content_type(ct: str) -> str:
    if not ct:
        return ''
    ct = ct.lower()
    if 'jpeg' in ct or 'jpg' in ct: return '.jpg'
    if 'png' in ct: return '.png'
    if 'gif' in ct: return '.gif'
    if 'webp' in ct: return '.webp'
    if 'mp4' in ct: return '.mp4'
    if 'mpeg' in ct: return '.mpg'
    return mimetypes.guess_extension(ct) or ''

def _cache_paths(media_id: str, content_type: str | None = None, kind: str = "image"):
    # procura arquivos já existentes desta variante
    prefix = f"{media_id}-{kind}."
    for name in os.listdir(MEDIA_CACHE_DIR):
        if name.startswith(prefix):
            p = os.path.join(MEDIA_CACHE_DIR, name)
            meta = os.path.join(MEDIA_CACHE_DIR, f"{media_id}-{kind}.meta")
            return p, meta
    ext = _ext_from_content_type(content_type) if content_type else '.bin'
    file_path = os.path.join(MEDIA_CACHE_DIR, f"{media_id}-{kind}{ext}")
    meta_path = os.path.join(MEDIA_CACHE_DIR, f"{media_id}-{kind}.meta")
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

def _save_stream_to_file(resp: requests.Response, dst_path: str, max_bytes: int, min_bytes: int = 64) -> str:
    """
    Salva stream respeitando um limite. Considera inválido se:
      - total < min_bytes
      - Content-Length existir e não bater.
    """
    tmp_path = dst_path + ".tmp"
    total = 0
    try:
        with open(tmp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    f.close()
                    os.remove(tmp_path)
                    return ''
                f.write(chunk)
        cl = resp.headers.get('Content-Length')
        if cl is not None:
            try:
                cl = int(cl)
                if cl > 0 and total != cl:
                    os.remove(tmp_path)
                    return ''
            except Exception:
                pass
        if total < min_bytes:
            os.remove(tmp_path)
            return ''
        if os.path.exists(dst_path):
            os.remove(dst_path)
        os.rename(tmp_path, dst_path)
        return dst_path
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return ''

def serve_file_with_range(path: str, content_type: str):
    """Serve arquivo do disco com suporte a Range (206)."""
    try:
        file_size = os.path.getsize(path)
    except Exception:
        return tiny_png_response()

    range_header = request.headers.get('Range')
    if not range_header:
        with open(path, 'rb') as f:
            data = f.read()
        resp = make_response(data)
        resp.headers['Content-Type'] = content_type
        resp.headers['Content-Length'] = str(file_size)
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Cache-Control'] = 'public, max-age=86400'
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
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp

# =========================================
# Instagram (Basic Display)
# =========================================
def ig_get(path_or_id: str, fields: str, extra: dict | None = None):
    """GET na Graph Instagram Basic Display."""
    if not ACCESS_TOKEN:
        raise RuntimeError("INSTAGRAM_ACCESS_TOKEN ausente")
    url = f"{GRAPH_API_URL.rstrip('/')}/{path_or_id.lstrip('/')}"
    params = {"fields": fields, "access_token": ACCESS_TOKEN}
    if extra:
        params.update(extra)
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def ig_get_url(full_url: str):
    r = requests.get(full_url, timeout=20)
    r.raise_for_status()
    return r.json()

def _pick_src_by_kind(info: dict, kind: str) -> str:
    mtype = (info.get("media_type") or "").upper()
    media_url = info.get("media_url")
    thumb_url = info.get("thumbnail_url")
    if kind == "thumbnail":
        return thumb_url or media_url or ""
    if kind == "video":
        return media_url if mtype == "VIDEO" else (media_url or thumb_url or "")
    # kind == image (default) → ideal p/ <img>
    if mtype == "VIDEO":
        return thumb_url or ""  # para vídeos, prefira thumbnail
    return media_url or thumb_url or ""

def ensure_media_cached(media_id: str, kind: str = "image") -> tuple[str, str]:
    """Garante mídia em cache; retorna (file_path, content_type)."""
    existing_file, existing_meta = _cache_paths(media_id, kind=kind)
    if os.path.exists(existing_file) and _is_cache_fresh(existing_file):
        return existing_file, _read_meta(existing_meta)

    info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
    src = _pick_src_by_kind(info, kind)
    if not src:
        return '', ''

    with requests.get(src, stream=True, timeout=30) as cdn:
        cdn.raise_for_status()
        ct = cdn.headers.get('Content-Type', 'application/octet-stream')
        file_path, meta_path = _cache_paths(media_id, ct, kind)
        saved_path = _save_stream_to_file(cdn, file_path, MEDIA_CACHE_MAX_BYTES)
    if saved_path:
        _write_meta(meta_path, ct)
        os.utime(saved_path, None)
        return saved_path, ct
    return '', ''

# =========================================
# Rotas Instagram
# =========================================
@app.route('/api/instagram/media_proxy', methods=['GET'])
def media_proxy():
    """
    /api/instagram/media_proxy?id=<id>&kind=image|video|thumbnail
    Sempre devolve 200 com mídia válida (ou placeholder PNG quando não der).
    """
    media_id = (request.args.get('id') or '').strip()
    kind = (request.args.get('kind') or 'image').lower()

    if not media_id:
        return tiny_png_response()

    try:
        file_path, ct = ensure_media_cached(media_id, kind)
        if file_path and os.path.exists(file_path):
            return serve_file_with_range(file_path, ct)
        # fallback: placeholder
        return tiny_png_response()
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, 'status_code', 500)
        details = None
        try:
            details = e.response.json()
        except Exception:
            details = getattr(e.response, 'text', '')
        print(f"[media_proxy] upstream error: status={status} details={details}")
        return tiny_png_response()
    except Exception as e:
        print(f"[media_proxy] internal error: {e}")
        return tiny_png_response()

@app.route('/api/instagram/proxy-image', methods=['GET'])
def proxy_image_legacy():
    """
    Mantém a MESMA URL já usada pelo front.
    Aceita:
      - ?id=<media_id>&kind=image|video|thumbnail → delega ao media_proxy
      - ?url=/api/instagram/media_proxy?id=...   → extrai id/kind e delega
      - ?url=<absoluta IG/CDN> → stream
      - valores undefined/null → PNG minúsculo (200)
    """
    # Caminho preferido: vir com id/kind
    mid = (request.args.get('id') or '').strip()
    kind = (request.args.get('kind') or 'image').lower()
    if mid:
        return media_proxy()

    raw = (request.args.get('url') or '').strip()
    if not raw or raw in ('undefined', 'null', 'None'):
        return tiny_png_response()

    # Normaliza absoluto
    url = urljoin(request.host_url, raw) if raw.startswith('/') else raw
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    myhost = request.host.split(':', 1)[0].lower()

    # Allowlist
    allowed = {
        myhost,
        'graph.instagram.com',
        'instagram.com', 'www.instagram.com',
        'scontent.cdninstagram.com',
    }
    if not (host in allowed or host.endswith('fna.fbcdn.net')):
        return tiny_png_response()

    # Se for seu próprio media_proxy → extrai id/kind e delega
    if host == myhost and parsed.path.startswith('/api/instagram/media_proxy'):
        q = parse_qs(parsed.query)
        mid = (q.get('id') or [''])[0]
        k = (q.get('kind') or ['image'])[0]
        if not mid:
            return tiny_png_response()
        # Chama internamente o handler
        with app.test_request_context(f"/api/instagram/media_proxy?id={mid}&kind={k}", method='GET', headers=request.headers):
            return media_proxy()

    # Caso contrário, stream direto da CDN do IG
    try:
        r = requests.get(url, stream=True, timeout=20)
        r.raise_for_status()
        return Response(
            r.iter_content(chunk_size=64 * 1024),
            content_type=r.headers.get('Content-Type', 'image/jpeg'),
            direct_passthrough=True,
            headers={'Cache-Control': 'public, max-age=86400'}
        )
    except Exception as e:
        print(f"[proxy-image] error url={url} err={e}")
        return tiny_png_response()

@app.route('/api/instagram/posts', methods=['GET'])
def get_user_posts():
    """
    Retorna lista de posts no formato esperado pelo seu front + instashow:
      - SEMPRE inclui `images` (array de {url}) e `image` (alias para a primeira).
      - As URLs de mídia apontam para /api/instagram/media_proxy (com &kind=image).
    """
    cache_key = "posts_me"
    cached = get_from_cache(cache_key)
    if cached:
        return jsonify(cached)

    if not ACCESS_TOKEN:
        return jsonify({"error": "Access Token não configurado"}), 500

    try:
        # Basic Display: "me/media"
        fields = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,children{id,media_type,media_url,thumbnail_url}"
        api_data = ig_get("me/media", fields)
        formatted_posts = []

        # Info básica do perfil (username)
        try:
            me = ig_get("me", "id,username")
            username = me.get("username")
        except Exception:
            username = None

        def cover_url(mid: str) -> str:
            # para vídeo e imagem, entregue SEMPRE uma imagem (kind=image)
            return f"/api/instagram/media_proxy?id={mid}&kind=image"

        for post in api_data.get("data", []):
            ptype = (post.get("media_type") or "").upper()
            pid = post.get("id")

            # monta media_items (compatibilidade com seu front atual)
            media_items = []
            images = []

            if ptype in ("IMAGE", "VIDEO"):
                mid = pid
                media_items.append({
                    "type": ptype.lower(),
                    "url": cover_url(mid),  # para <img> é melhor entregar imagem
                    "cover": {
                        "thumbnail": {
                            "url": cover_url(mid),
                            "width": 1080.0,
                            "height": 1920.0
                        },
                        "standard": None,
                        "original": None
                    },
                    "id": mid
                })
                # **IMPORTANTE**: array "images" que o instashow usa na MODAL
                images.append({"url": cover_url(mid)})

            elif ptype == "CAROUSEL_ALBUM":
                for child in (post.get("children") or {}).get("data", []):
                    cmid = child.get("id")
                    ctype = (child.get("media_type") or "").upper()
                    media_items.append({
                        "type": ctype.lower(),
                        "url": cover_url(cmid),
                        "cover": {
                            "thumbnail": {
                                "url": cover_url(cmid),
                                "width": 1080.0,
                                "height": 1920.0
                            },
                            "standard": None,
                            "original": None
                        },
                        "id": cmid
                    })
                    images.append({"url": cover_url(cmid)})

            # Fallback: nunca deixe vazio para não quebrar o instashow
            if not images:
                images = [{"url": "/api/instagram/proxy-image?url=/static/instagram/placeholder.png"}]

            formatted_post = {
                "vendorId": pid,
                "type": ptype.lower().replace("_album", ""),
                "link": post.get("permalink"),
                "publishedAt": post.get("timestamp"),
                "author": {
                    "username": username,
                    "url": None,
                    "profilePictureUrl": None,
                    "isVerifiedProfile": None,
                    "name": None,
                    "biography": None,
                    "postsCount": None,
                    "followersCount": None,
                    "followingCount": None
                },
                "media": media_items,
                "images": images,                 # <== chave usada pelo instashow na MODAL
                "image": images[0]["url"],        # <== alias comum
                "comments": [],
                "caption": post.get("caption"),
                "commentsCount": None,
                "likesCount": None,
                "extra": {"platform": "instagram"},
                "isPinned": None
            }
            formatted_posts.append(formatted_post)

        final_response = {"code": 200, "payload": formatted_posts}
        set_in_cache(cache_key, final_response)
        return jsonify(final_response)

    except requests.exceptions.RequestException as e:
        print(f"[posts] IG error: {e}")
        error_payload = {"error": str(e)}
        if e.response is not None:
            try:
                error_payload["details"] = e.response.json()
            except ValueError:
                error_payload["details"] = e.response.text
        return jsonify(error_payload), getattr(e.response, 'status_code', 500)
    except Exception as e:
        print(f"[posts] internal error: {e}")
        return jsonify({"error": str(e)}), 500

# =========================================
# Static / health
# =========================================
@app.route('/static/instagram/<path:filename>')
def serve_instagram_static(filename):
    return send_from_directory('static/instagram', filename)

@app.route('/health')
def health():
    return {'status': 'ok'}, 200

# =========================================
# CLI / Main
# =========================================
def cli_warmup(limit: int, force: bool):
    # opcional: fazer uma passada em me/media e cachear thumbs
    try:
        data = ig_get("me/media", "id,media_type,thumbnail_url")
        count = 0
        for item in (data.get("data") or []):
            mid = item.get("id")
            if not mid:
                continue
            ensure_media_cached(mid, "image")
            time.sleep(WARMUP_SLEEP_SECONDS)
            count += 1
            if count >= limit:
                break
        print(f"WARMUP => cached={count}")
    except Exception as e:
        print("WARMUP ERROR:", e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Instagram API proxy com cache")
    parser.add_argument('--warmup', action='store_true')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()

    if args.warmup:
        cli_warmup(limit=args.limit, force=False)
    else:
        # Produção costuma rodar atrás de um proxy; para testes locais:
        app.run(host='0.0.0.0', port=args.port, debug=True)
