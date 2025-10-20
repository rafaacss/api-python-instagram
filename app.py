import os, time, mimetypes, argparse, requests
from flask import Flask, jsonify, request, Response, send_from_directory, abort, make_response
from dotenv import load_dotenv
from flask_cors import CORS
from urllib.parse import urlparse, urljoin, parse_qs

load_dotenv()
app = Flask(__name__, static_folder='static')
CORS(app)

# ------------------ Config ------------------
ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
GRAPH_API_URL = 'https://graph.instagram.com/v22.0'

MEDIA_CACHE_DIR = os.getenv('MEDIA_CACHE_DIR', '/tmp/instagram-cache')
os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)
MEDIA_CACHE_TTL_SECONDS = int(os.getenv('MEDIA_CACHE_TTL_SECONDS', '3600'))
MEDIA_CACHE_MAX_BYTES = int(os.getenv('MEDIA_CACHE_MAX_BYTES', str(100 * 1024 * 1024)))

# ------------------ tiny png fallback ------------------
_TINY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x02\x00\x01'
    b'\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82'
)
def _tiny_png_response():
    resp = Response(_TINY_PNG, status=200, mimetype='image/png')
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp

# ------------------ Cache helpers ------------------
def _ext_from_content_type(ct: str):
    if not ct: return ''
    ct = ct.lower()
    for key, ext in [('jpeg', '.jpg'), ('jpg', '.jpg'), ('png', '.png'),
                     ('gif', '.gif'), ('webp', '.webp'), ('mp4', '.mp4')]:
        if key in ct: return ext
    return mimetypes.guess_extension(ct) or ''

def _cache_paths(mid, content_type=None, kind='image'):
    prefix = f"{mid}-{kind}."
    for name in os.listdir(MEDIA_CACHE_DIR):
        if name.startswith(prefix):
            return os.path.join(MEDIA_CACHE_DIR, name), os.path.join(MEDIA_CACHE_DIR, f"{mid}-{kind}.meta")
    ext = _ext_from_content_type(content_type) if content_type else '.bin'
    return (os.path.join(MEDIA_CACHE_DIR, f"{mid}-{kind}{ext}"),
            os.path.join(MEDIA_CACHE_DIR, f"{mid}-{kind}.meta"))

def _is_cache_fresh(path):
    return os.path.exists(path) and (time.time() - os.path.getmtime(path)) <= MEDIA_CACHE_TTL_SECONDS

def _read_meta(path):
    try:
        return open(path).read().strip()
    except Exception:
        return 'application/octet-stream'

def _write_meta(path, ct):
    try:
        open(path, 'w').write(ct or 'application/octet-stream')
    except Exception:
        pass

def drop_media_cache(mid):
    for f in os.listdir(MEDIA_CACHE_DIR):
        if f.startswith(mid + "-"):
            try:
                os.remove(os.path.join(MEDIA_CACHE_DIR, f))
            except Exception:
                pass

# ------------------ Instagram helpers ------------------
def ig_get(id_or_path, fields):
    r = requests.get(f"{GRAPH_API_URL.rstrip('/')}/{id_or_path.lstrip('/')}",
                     params={"fields": fields, "access_token": ACCESS_TOKEN},
                     timeout=15)
    r.raise_for_status()
    return r.json()

def _pick_src_by_kind(info, kind):
    t = (info.get('media_type') or '').upper()
    m, th = info.get('media_url'), info.get('thumbnail_url')
    if kind == 'thumbnail':
        return th or m or ''
    if kind == 'video':
        return m if t == 'VIDEO' else (m or th or '')
    # kind image (para <img>): se for vídeo, prioriza thumbnail
    if t == 'VIDEO':
        return th or ''
    return m or th or ''

def ensure_media_cached(mid, kind='image'):
    f, meta = _cache_paths(mid, kind=kind)
    if _is_cache_fresh(f):
        return f, _read_meta(meta)
    try:
        info = ig_get(mid, 'media_type,media_url,thumbnail_url')
        src = _pick_src_by_kind(info, kind)
        if not src:
            return '', ''
        with requests.get(src, stream=True, timeout=20) as cdn:
            cdn.raise_for_status()
            ct = cdn.headers.get('Content-Type', 'application/octet-stream')
            path, _meta = _cache_paths(mid, ct, kind)
            tmp = path + '.tmp'
            total = 0
            with open(tmp, 'wb') as out:
                for c in cdn.iter_content(65536):
                    if not c:
                        continue
                    total += len(c)
                    if total > MEDIA_CACHE_MAX_BYTES:
                        os.remove(tmp)
                        return '', ''
                    out.write(c)
            if total < 32:
                os.remove(tmp)
                return '', ''
            os.rename(tmp, path)
            _write_meta(_meta, ct)
            return path, ct
    except Exception as e:
        print(f"[ensure_media_cached] fail {mid}: {e}")
        return '', ''
    return '', ''

# ------------------ Serve helpers ------------------
def serve_file(path, ct):
    if not os.path.exists(path):
        return _tiny_png_response()
    data = open(path, 'rb').read()
    r = Response(data, mimetype=ct)
    r.headers['Cache-Control'] = 'public, max-age=86400'
    return r

def handle_media_proxy(mid, kind='image'):
    if not mid:
        return _tiny_png_response()
    try:
        f, ct = ensure_media_cached(mid, kind)
        if f:
            return serve_file(f, ct)
        return _tiny_png_response()
    except Exception as e:
        print(f"[media_proxy] internal {mid}: {e}")
        return _tiny_png_response()

# ------------------ Rotas API ------------------
@app.route('/api/instagram/media_proxy')
def media_proxy():
    mid = request.args.get('id')
    kind = (request.args.get('kind') or 'image').lower()
    return handle_media_proxy(mid, kind)

@app.route('/api/instagram/proxy-image')
def proxy_image_legacy():
    """
    Compat: aceita ?id=... (preferível) ou ?url=... (pode ser /api/instagram/media_proxy?id=...).
    Se url/id estiver vazio/undefined → retorna PNG 1x1 (200).
    """
    mid = (request.args.get('id') or '').strip()
    kind = (request.args.get('kind') or 'image').lower()
    if mid:
        return handle_media_proxy(mid, kind)

    raw = (request.args.get('url') or '').strip()
    if not raw or raw in ('undefined', 'null', 'None'):
        return _tiny_png_response()

    url = urljoin(request.host_url, raw) if raw.startswith('/') else raw
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    myhost = request.host.split(':', 1)[0].lower()

    allowed = {myhost, 'graph.instagram.com', 'instagram.com', 'www.instagram.com', 'scontent.cdninstagram.com'}
    if not (host in allowed or host.endswith('fna.fbcdn.net')):
        return _tiny_png_response()

    try:
        if host == myhost and parsed.path.startswith('/api/instagram/media_proxy'):
            q = parse_qs(parsed.query)
            mid = (q.get('id') or [''])[0]
            kind = (q.get('kind') or ['image'])[0]
            return handle_media_proxy(mid, kind)

        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        return Response(
            r.iter_content(65536),
            content_type=r.headers.get('Content-Type', 'image/jpeg'),
            direct_passthrough=True
        )
    except Exception as e:
        print(f"[proxy-image] error {url}: {e}")
        return _tiny_png_response()

# ------------------ Páginas estáticas / atalho ------------------
@app.route("/")
def root_index():
    return send_from_directory('static/instagram', 'index.html')

@app.route("/static/instagram/")
def instagram_dir_index():
    return send_from_directory('static/instagram', 'index.html')

@app.route("/instagram.js")
def instagram_js_shortcut():
    return send_from_directory('static/instagram', 'instagram.js')

# ------------------ Health & errors ------------------
@app.route('/health')
def health():
    return {'status': 'ok'}, 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not_found", "path": request.path}), 404

@app.errorhandler(500)
def internal(e):
    return jsonify({"error": "internal_error"}), 500

# ------------------ Main ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
