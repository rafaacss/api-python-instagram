import os
import time
import mimetypes
import argparse
import requests
import logging
from flask import Flask, jsonify, request, Response, send_from_directory, abort, make_response
from dotenv import load_dotenv
from flask_cors import CORS
from urllib.parse import urlparse, urljoin, parse_qs, unquote
from urllib.error import URLError

# =========================================
# Bootstrap & Logging
# =========================================
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

# =========================================
# Config
# =========================================
ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN', '').strip()
GRAPH_API_URL = os.getenv('GRAPH_API_URL', 'https://graph.instagram.com/v22.0')

CACHE_DURATION_SECONDS = int(os.getenv('CACHE_DURATION_SECONDS', '3600'))
MEDIA_CACHE_DIR = os.getenv('MEDIA_CACHE_DIR', '/var/cache/instagram')
MEDIA_CACHE_TTL_SECONDS = int(os.getenv('MEDIA_CACHE_TTL_SECONDS', '3600'))
MEDIA_CACHE_MAX_BYTES = int(os.getenv('MEDIA_CACHE_MAX_BYTES', str(100 * 1024 * 1024)))
WARMUP_SLEEP_SECONDS = float(os.getenv('WARMUP_SLEEP_SECONDS', '0.25'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))

# Criar diretório de cache com permissões corretas
try:
    os.makedirs(MEDIA_CACHE_DIR, exist_ok=True)
    logger.info(f"✓ Cache directory ready: {MEDIA_CACHE_DIR}")
except Exception as e:
    logger.error(f"✗ Failed to create cache directory: {e}")
    raise

# Validar variáveis críticas
if not ACCESS_TOKEN:
    logger.warning("⚠ INSTAGRAM_ACCESS_TOKEN não configurado!")

# Cache em memória simples p/ JSON
api_cache: dict[str, dict] = {}

# PNG minúsculo como placeholder
_TINY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x02\x00\x01'
    b'\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82'
)

def tiny_png_response(max_age=300):
    """Retorna PNG minúsculo como fallback"""
    r = Response(_TINY_PNG, status=200, mimetype='image/png')
    r.headers['Cache-Control'] = f'public, max-age={max_age}'
    return r

# =========================================
# Helpers para URL Generation
# =========================================
def generate_proxy_image_url(media_id: str, kind: str = "image") -> str:
    """
    Gera URL corretamente encodada para proxy-image.

    Uso recomendado em templates/frontend:
      <img src="{{ generate_proxy_image_url('123456', 'image') }}" />

    Retorna:
      /api/instagram/proxy-image?url=%2Fapi%2Finstagram%2Fmedia_proxy%3Fid%3D123456%26kind%3Dimage
    """
    from urllib.parse import quote
    inner_url = f"/api/instagram/media_proxy?id={media_id}&kind={kind}"
    encoded = quote(inner_url, safe='')
    return f"/api/instagram/proxy-image?url={encoded}"

# =========================================
# Helpers de cache JSON
# =========================================
def get_from_cache(key: str):
    """Recupera valor do cache JSON em memória"""
    item = api_cache.get(key)
    if not item:
        return None
    if (time.time() - item["ts"]) > CACHE_DURATION_SECONDS:
        api_cache.pop(key, None)
        return None
    return item["data"]

def set_in_cache(key: str, data):
    """Armazena valor no cache JSON em memória"""
    api_cache[key] = {"data": data, "ts": time.time()}

# =========================================
# Helpers de mídia/cache em disco
# =========================================
def _ext_from_content_type(ct: str) -> str:
    """Extrai extensão de arquivo baseado no Content-Type"""
    if not ct:
        return ''
    ct = ct.lower()
    if 'jpeg' in ct or 'jpg' in ct:
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

def _cache_paths(media_id: str, content_type: str | None = None, kind: str = "image"):
    """Retorna (file_path, meta_path) para mídia cacheada"""
    prefix = f"{media_id}-{kind}."

    # Procura arquivos já existentes desta variante
    try:
        for name in os.listdir(MEDIA_CACHE_DIR):
            if name.startswith(prefix) and not name.endswith('.meta'):
                p = os.path.join(MEDIA_CACHE_DIR, name)
                meta = os.path.join(MEDIA_CACHE_DIR, f"{media_id}-{kind}.meta")
                return p, meta
    except Exception as e:
        logger.warning(f"Erro ao listar cache dir: {e}")

    ext = _ext_from_content_type(content_type) if content_type else '.bin'
    file_path = os.path.join(MEDIA_CACHE_DIR, f"{media_id}-{kind}{ext}")
    meta_path = os.path.join(MEDIA_CACHE_DIR, f"{media_id}-{kind}.meta")
    return file_path, meta_path

def _write_meta(meta_path: str, content_type: str):
    """Escreve metadados (Content-Type) para arquivo cacheado"""
    try:
        with open(meta_path, 'w') as f:
            f.write(content_type or 'application/octet-stream')
    except Exception as e:
        logger.warning(f"Erro ao escrever meta: {e}")

def _read_meta(meta_path: str) -> str:
    """Lê metadados (Content-Type) do arquivo cacheado"""
    try:
        with open(meta_path, 'r') as f:
            return f.read().strip()
    except Exception:
        return 'application/octet-stream'

def _is_cache_fresh(file_path: str) -> bool:
    """Verifica se arquivo em cache ainda é válido"""
    if not os.path.exists(file_path):
        return False
    age = time.time() - os.path.getmtime(file_path)
    return age <= MEDIA_CACHE_TTL_SECONDS

def _save_stream_to_file(resp: requests.Response, dst_path: str, max_bytes: int, min_bytes: int = 64) -> str:
    """
    Salva stream respeitando limites de tamanho.
    Considera inválido se: total < min_bytes ou Content-Length não bater.
    """
    tmp_path = dst_path + ".tmp"
    total = 0
    try:
        logger.debug(f"[_save_stream_to_file] Iniciando save para {dst_path}")
        with open(tmp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    logger.error(f"❌ Arquivo excedeu limite: {total} > {max_bytes}")
                    f.close()
                    os.remove(tmp_path)
                    return ''
                f.write(chunk)

        logger.debug(f"[_save_stream_to_file] Download completo: {total} bytes")

        # Validar Content-Length
        cl = resp.headers.get('Content-Length')
        if cl is not None:
            try:
                cl = int(cl)
                if cl > 0 and total != cl:
                    logger.error(f"❌ Content-Length mismatch: recebido={total}, header={cl}")
                    os.remove(tmp_path)
                    return ''
            except Exception as e:
                logger.debug(f"Erro ao validar Content-Length: {e}")

        if total < min_bytes:
            logger.error(f"❌ Arquivo muito pequeno: {total} < {min_bytes}")
            os.remove(tmp_path)
            return ''

        if os.path.exists(dst_path):
            logger.debug(f"Removendo arquivo anterior: {dst_path}")
            os.remove(dst_path)

        os.rename(tmp_path, dst_path)
        logger.info(f"✓ Arquivo salvo: {dst_path} ({total} bytes)")
        return dst_path
    except Exception as e:
        logger.error(f"❌ Erro ao salvar stream: {e}", exc_info=True)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return ''

def serve_file_with_range(path: str, content_type: str):
    """Serve arquivo do disco com suporte a Range requests (206)"""
    try:
        file_size = os.path.getsize(path)
    except Exception as e:
        logger.warning(f"Arquivo não encontrado: {path}")
        return tiny_png_response()

    range_header = request.headers.get('Range')
    if not range_header:
        # Retornar arquivo inteiro
        try:
            with open(path, 'rb') as f:
                data = f.read()
            resp = make_response(data)
            resp.headers['Content-Type'] = content_type
            resp.headers['Content-Length'] = str(file_size)
            resp.headers['Accept-Ranges'] = 'bytes'
            resp.headers['Cache-Control'] = 'public, max-age=86400'
            return resp
        except Exception as e:
            logger.error(f"Erro ao ler arquivo: {e}")
            return tiny_png_response()

    # Processar Range request
    try:
        units, rng = range_header.split('=')
        if units != 'bytes':
            raise ValueError("Invalid range unit")
        start_str, end_str = rng.split('-')
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start < 0:
            raise ValueError("Invalid range values")
    except Exception as e:
        logger.warning(f"Range header inválido: {range_header}")
        return Response(status=416)

    length = end - start + 1
    try:
        with open(path, 'rb') as f:
            f.seek(start)
            chunk = f.read(length)
        resp = Response(chunk, status=206, mimetype=content_type)
        resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        resp.headers['Accept-Ranges'] = 'bytes'
        resp.headers['Content-Length'] = str(length)
        resp.headers['Cache-Control'] = 'public, max-age=86400'
        return resp
    except Exception as e:
        logger.error(f"Erro ao servir range: {e}")
        return tiny_png_response()

# =========================================
# Instagram (Basic Display)
# =========================================
def ig_get(path_or_id: str, fields: str, extra: dict | None = None):
    """GET na Graph Instagram Basic Display"""
    if not ACCESS_TOKEN:
        raise RuntimeError("INSTAGRAM_ACCESS_TOKEN não configurado")

    url = f"{GRAPH_API_URL.rstrip('/')}/{path_or_id.lstrip('/')}"
    params = {"fields": fields, "access_token": ACCESS_TOKEN}
    if extra:
        params.update(extra)

    logger.debug(f"[ig_get] url={url}")
    r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()

def ig_get_url(full_url: str):
    """GET em URL completa do Instagram"""
    logger.debug(f"[ig_get_url] url={full_url}")
    r = requests.get(full_url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()

def _pick_src_by_kind(info: dict, kind: str) -> str:
    """Seleciona URL de mídia baseado no tipo (image/video/thumbnail)"""
    mtype = (info.get("media_type") or "").upper()
    media_url = info.get("media_url", "").strip()
    thumb_url = info.get("thumbnail_url", "").strip()

    if kind == "thumbnail":
        return thumb_url or media_url or ""
    if kind == "video":
        return media_url if mtype == "VIDEO" else (media_url or thumb_url or "")
    # kind == image (default)
    if mtype == "VIDEO":
        return thumb_url or ""
    return media_url or thumb_url or ""

def ensure_media_cached(media_id: str, kind: str = "image") -> tuple[str, str]:
    """Garante mídia em cache; retorna (file_path, content_type)"""
    if not media_id or not media_id.strip():
        logger.warning("❌ Media ID vazio")
        return '', ''

    media_id = media_id.strip()
    existing_file, existing_meta = _cache_paths(media_id, kind=kind)

    # Verificar se já está em cache e fresco
    if os.path.exists(existing_file) and _is_cache_fresh(existing_file):
        ct = _read_meta(existing_meta)
        logger.info(f"✓ Cache HIT: {media_id}-{kind} | file={existing_file} | ct={ct}")
        return existing_file, ct

    logger.info(f"→ CACHE MISS: Buscando mídia {media_id}-{kind}")

    try:
        if not ACCESS_TOKEN:
            logger.error(f"❌ ACCESS_TOKEN não configurado!")
            return '', ''

        logger.debug(f"[ensure_media_cached] Buscando info do IG para {media_id}")
        info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
        logger.debug(f"[ensure_media_cached] Info recebido: {info}")

        src = _pick_src_by_kind(info, kind)
        logger.info(f"[ensure_media_cached] URL selecionada (kind={kind}): {src[:80] if src else 'VAZIA'}")

        if not src:
            logger.warning(f"❌ Nenhuma URL disponível para {media_id} (kind={kind})")
            logger.warning(f"   media_type={info.get('media_type')}")
            logger.warning(f"   media_url={info.get('media_url', '')[:80]}")
            logger.warning(f"   thumbnail_url={info.get('thumbnail_url', '')[:80]}")
            return '', ''

        logger.info(f"[ensure_media_cached] Iniciando download de: {src[:80]}...")

        with requests.get(src, stream=True, timeout=REQUEST_TIMEOUT) as cdn:
            cdn.raise_for_status()
            ct = cdn.headers.get('Content-Type', 'application/octet-stream')
            content_length = cdn.headers.get('Content-Length', 'unknown')
            logger.info(f"[ensure_media_cached] Status={cdn.status_code} | CT={ct} | CL={content_length}")

            file_path, meta_path = _cache_paths(media_id, ct, kind)
            logger.info(f"[ensure_media_cached] Cache path: {file_path}")

            saved_path = _save_stream_to_file(cdn, file_path, MEDIA_CACHE_MAX_BYTES)

        if saved_path:
            _write_meta(meta_path, ct)
            os.utime(saved_path, None)
            file_size = os.path.getsize(saved_path)
            logger.info(f"✓ Arquivo cacheado com sucesso: {saved_path} ({file_size} bytes)")
            return saved_path, ct
        else:
            logger.error(f"❌ Falha ao salvar arquivo")
            return '', ''

    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if hasattr(e, 'response') and e.response else 'unknown'
        logger.error(f"❌ Erro de request IG: status={status_code} | {e}", exc_info=True)
        return '', ''
    except Exception as e:
        logger.error(f"❌ Erro ao cachear mídia {media_id}: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return '', ''

# =========================================
# Rotas Instagram
# =========================================
@app.route('/api/instagram/media_proxy', methods=['GET', 'OPTIONS'])
def media_proxy():
    """
    GET /api/instagram/media_proxy?id=<id>&kind=image|video|thumbnail
    Sempre devolve 200 com mídia válida (ou placeholder PNG quando não der).
    """
    if request.method == 'OPTIONS':
        return '', 204

    media_id = (request.args.get('id') or '').strip()
    kind = (request.args.get('kind') or 'image').lower()

    logger.info(f"\n{'='*60}")
    logger.info(f"[media_proxy] NOVA REQUISIÇÃO")
    logger.info(f"  media_id: {media_id}")
    logger.info(f"  kind: {kind}")
    logger.info(f"{'='*60}")

    if not media_id:
        logger.error("[media_proxy] ❌ ID vazio!")
        return tiny_png_response()

    try:
        # Validar que o token está configurado
        if not ACCESS_TOKEN:
            logger.error("[media_proxy] ❌ INSTAGRAM_ACCESS_TOKEN não configurado!")
            return tiny_png_response()

        logger.info(f"[media_proxy] → Iniciando ensure_media_cached...")
        file_path, ct = ensure_media_cached(media_id, kind)

        logger.info(f"[media_proxy] Resultado: file_path={file_path}, ct={ct}")

        if file_path and os.path.exists(file_path):
            logger.info(f"[media_proxy] ✓ Arquivo existe, servindo...")
            return serve_file_with_range(file_path, ct)

        logger.error(f"[media_proxy] ❌ Arquivo não encontrado: {file_path}")
        logger.error(f"[media_proxy] Retornando PNG placeholder")
        return tiny_png_response()

    except requests.exceptions.RequestException as e:
        status = getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
        logger.error(f"[media_proxy] ❌ Upstream error: status={status}", exc_info=True)
        return tiny_png_response()
    except Exception as e:
        logger.error(f"[media_proxy] ❌ Internal error: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return tiny_png_response()

@app.route('/api/instagram/proxy-image', methods=['GET', 'OPTIONS'])
def proxy_image_legacy():
    """
    Mantém compatibilidade com URLs antigas.

    Aceita múltiplos formatos:
      1. ?id=<media_id>&kind=image|video|thumbnail (RECOMENDADO)
      2. ?url=/api/instagram/media_proxy?id=...&kind=... (URL encoding necessário!)
      3. ?url=<absoluta IG/CDN>
      4. undefined/null → PNG minúsculo (200)

    IMPORTANTE: Se receber ?url=/api/instagram/media_proxy&id=X&kind=Y
    (parâmetros desmembrados), reconstrói a URL interna.
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        # ==========================================
        # PASSO 1: Verificar se vem com id/kind direto
        # ==========================================
        mid = (request.args.get('id') or '').strip()
        kind = (request.args.get('kind') or 'image').lower()
        raw_url = (request.args.get('url') or '').strip()

        logger.info(f"[proxy-image] START")
        logger.info(f"  - id param: {mid}")
        logger.info(f"  - kind param: {kind}")
        logger.info(f"  - url param: {raw_url[:80] if raw_url else 'NONE'}")

        # ==========================================
        # PASSO 2: Detectar URL desmembrada
        # ==========================================
        # Se recebeu ?url=/api/instagram/media_proxy&id=X&kind=Y
        # (parâmetros separados), reconstrói a URL interna
        if (raw_url and '/api/instagram/media_proxy' in raw_url and
            ('id' in request.args or 'kind' in request.args)):

            logger.info(f"[proxy-image] ✓ Detectado formato desmembrado!")
            logger.info(f"  - Reconstruindo URL interna com id={mid} kind={kind}")

            # Se ambos vêm como parâmetros top-level, use media_proxy direto
            if mid:
                with app.test_request_context(f"/api/instagram/media_proxy?id={mid}&kind={kind}", method='GET', headers=request.headers):
                    return media_proxy()

        # ==========================================
        # PASSO 3: Se vem com id/kind direto (sem url)
        # ==========================================
        if mid and not raw_url:
            logger.info(f"[proxy-image] ✓ Usando id direto, delegando para media_proxy")
            return media_proxy()

        # ==========================================
        # PASSO 4: Processar parâmetro url
        # ==========================================
        if not raw_url or raw_url in ('undefined', 'null', 'None'):
            logger.warning("[proxy-image] ❌ URL vazia ou undefined")
            return tiny_png_response()

        # Decodificar URL se necessário
        try:
            decoded = unquote(raw_url)
            if decoded != raw_url:
                logger.info(f"[proxy-image] URL decodificada: {decoded[:80]}")
            raw_url = decoded
        except Exception as e:
            logger.warning(f"[proxy-image] Erro ao decodificar URL: {e}")

        # Normalizar URL
        url = urljoin(request.host_url, raw_url) if raw_url.startswith('/') else raw_url
        logger.info(f"[proxy-image] URL normalizada: {url[:100]}")

        parsed = urlparse(url)
        host = (parsed.hostname or '').lower()
        myhost = request.host.split(':', 1)[0].lower()

        logger.info(f"[proxy-image] HOST CHECK | host={host} | myhost={myhost}")

        # ==========================================
        # PASSO 5: Validar host (allowlist)
        # ==========================================
        allowed = {
            myhost,
            'graph.instagram.com',
            'instagram.com', 'www.instagram.com',
            'scontent.cdninstagram.com',
        }

        is_allowed = (host in allowed or host.endswith('fna.fbcdn.net'))
        if not is_allowed:
            logger.warning(f"[proxy-image] ❌ Host não permitido: {host}")
            return tiny_png_response()

        # ==========================================
        # PASSO 6: Se for media_proxy interno → delega
        # ==========================================
        if host == myhost and '/api/instagram/media_proxy' in parsed.path:
            logger.info("[proxy-image] ✓ Detectado media_proxy interno, extraindo parâmetros...")
            try:
                q = parse_qs(parsed.query)
                logger.debug(f"[proxy-image] Query parsed: {q}")
                mid = (q.get('id') or [''])[0].strip()
                k = (q.get('kind') or ['image'])[0].strip()
                logger.info(f"[proxy-image] Extraído | mid={mid} | kind={k}")
                if not mid:
                    logger.warning("[proxy-image] Media ID vazio após extração")
                    return tiny_png_response()
                with app.test_request_context(f"/api/instagram/media_proxy?id={mid}&kind={k}", method='GET', headers=request.headers):
                    return media_proxy()
            except Exception as e:
                logger.error(f"[proxy-image] ❌ Erro ao processar media_proxy interno: {e}", exc_info=True)
                return tiny_png_response()

        # ==========================================
        # PASSO 7: Stream direto da CDN
        # ==========================================
        logger.info(f"[proxy-image] → Streamando direto da CDN: {url[:80]}...")
        try:
            r = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            ct = r.headers.get('Content-Type', 'image/jpeg')
            logger.info(f"[proxy-image] ✓ CDN stream OK | content-type={ct}")
            return Response(
                r.iter_content(chunk_size=64 * 1024),
                content_type=ct,
                direct_passthrough=True,
                headers={'Cache-Control': 'public, max-age=86400'}
            )
        except Exception as e:
            logger.error(f"[proxy-image] ❌ Erro CDN stream: {e}", exc_info=True)
            return tiny_png_response()

    except Exception as e:
        logger.error(f"[proxy-image] ❌ Erro geral: {e}", exc_info=True)
        return tiny_png_response()

@app.route('/api/instagram/posts', methods=['GET', 'OPTIONS'])
def get_user_posts():
    """
    GET /api/instagram/posts
    Retorna lista de posts com URLs apontando para /api/instagram/media_proxy
    """
    if request.method == 'OPTIONS':
        return '', 204

    cache_key = "posts_me"
    cached = get_from_cache(cache_key)
    if cached:
        logger.info("[posts] Retornando do cache")
        return jsonify(cached)

    if not ACCESS_TOKEN:
        logger.error("[posts] ACCESS_TOKEN não configurado")
        return jsonify({"error": "Access Token não configurado"}), 500

    try:
        logger.info("[posts] Buscando posts do Instagram...")
        fields = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,children{id,media_type,media_url,thumbnail_url}"
        api_data = ig_get("me/media", fields)
        formatted_posts = []

        # Info básica do perfil
        try:
            me = ig_get("me", "id,username")
            username = me.get("username")
            logger.info(f"[posts] Username: {username}")
        except Exception as e:
            logger.warning(f"[posts] Erro ao buscar username: {e}")
            username = None

        def cover_url(mid: str) -> str:
            return f"/api/instagram/media_proxy?id={mid}&kind=image"

        for post in api_data.get("data", []):
            ptype = (post.get("media_type") or "").upper()
            pid = post.get("id")

            if not pid:
                logger.warning("[posts] Post sem ID, pulando")
                continue

            media_items = []
            images = []

            if ptype in ("IMAGE", "VIDEO"):
                mid = pid
                media_url = cover_url(mid)
                media_items.append({
                    "type": ptype.lower(),
                    "url": media_url,
                    "cover": {
                        "thumbnail": {
                            "url": media_url,
                            "width": 1080.0,
                            "height": 1920.0
                        },
                        "standard": None,
                        "original": None
                    },
                    "id": mid
                })
                images.append({"url": media_url})

            elif ptype == "CAROUSEL_ALBUM":
                for child in (post.get("children") or {}).get("data", []):
                    cmid = child.get("id")
                    if not cmid:
                        continue
                    ctype = (child.get("media_type") or "").upper()
                    child_url = cover_url(cmid)
                    media_items.append({
                        "type": ctype.lower(),
                        "url": child_url,
                        "cover": {
                            "thumbnail": {
                                "url": child_url,
                                "width": 1080.0,
                                "height": 1920.0
                            },
                            "standard": None,
                            "original": None
                        },
                        "id": cmid
                    })
                    images.append({"url": child_url})

            # Fallback
            if not images:
                placeholder_url = "/api/instagram/proxy-image?url=/static/instagram/placeholder.png"
                images = [{"url": placeholder_url}]
                if not media_items:
                    media_items.append({
                        "type": "image",
                        "url": placeholder_url,
                        "cover": {
                            "thumbnail": {
                                "url": placeholder_url,
                                "width": 1080.0,
                                "height": 1920.0
                            },
                            "standard": None,
                            "original": None
                        },
                        "id": "placeholder"
                    })

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
                "images": images,
                "image": images[0]["url"] if images else "",
                "comments": [],
                "caption": post.get("caption"),
                "commentsCount": None,
                "likesCount": None,
                "extra": {"platform": "instagram"},
                "isPinned": None
            }
            formatted_posts.append(formatted_post)

        logger.info(f"[posts] Retornando {len(formatted_posts)} posts")
        for idx, post in enumerate(formatted_posts[:3]):
            logger.info(f"  Post {idx}: {post.get('vendorId')} | {len(post.get('images', []))} images")

        final_response = {"code": 200, "payload": formatted_posts}
        set_in_cache(cache_key, final_response)
        return jsonify(final_response)

    except requests.exceptions.RequestException as e:
        logger.error(f"[posts] IG error: {e}")
        error_payload = {"error": str(e)}
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_payload["details"] = e.response.json()
            except ValueError:
                error_payload["details"] = e.response.text
        return jsonify(error_payload), getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
    except Exception as e:
        logger.error(f"[posts] internal error: {e}")
        return jsonify({"error": str(e)}), 500

# =========================================
# Static / Health
# =========================================
@app.route('/static/instagram/<path:filename>')
def serve_instagram_static(filename):
    """Serve arquivos estáticos"""
    return send_from_directory('static/instagram', filename)

@app.route('/health', methods=['GET'])
def health():
    """Health check com informações de debug"""
    checks = {
        'status': 'ok',
        'cache_dir_exists': os.path.exists(MEDIA_CACHE_DIR),
        'cache_dir_writable': os.access(MEDIA_CACHE_DIR, os.W_OK) if os.path.exists(MEDIA_CACHE_DIR) else False,
        'token_configured': bool(ACCESS_TOKEN),
        'token_length': len(ACCESS_TOKEN) if ACCESS_TOKEN else 0,
        'graph_api_url': GRAPH_API_URL,
        'cache_dir': MEDIA_CACHE_DIR,
        'request_timeout_seconds': REQUEST_TIMEOUT
    }

    # Tentar conexão com Instagram
    if ACCESS_TOKEN:
        try:
            r = requests.get(
                f"{GRAPH_API_URL}/me",
                params={"fields": "id", "access_token": ACCESS_TOKEN},
                timeout=5
            )
            checks['instagram_api_ok'] = r.status_code == 200
            if r.status_code != 200:
                checks['instagram_error'] = f"Status {r.status_code}"
        except Exception as e:
            checks['instagram_api_ok'] = False
            checks['instagram_error'] = str(e)
    else:
        checks['instagram_api_ok'] = False
        checks['instagram_error'] = "Token não configurado"

    return jsonify(checks), 200

@app.route('/api/instagram/clear-cache', methods=['POST', 'GET'])
def clear_cache():
    """Limpa todo o cache (JSON em memória + disco)"""
    global api_cache

    cache_size = len(api_cache)
    api_cache.clear()

    media_files_deleted = 0
    if os.path.exists(MEDIA_CACHE_DIR):
        try:
            for filename in os.listdir(MEDIA_CACHE_DIR):
                file_path = os.path.join(MEDIA_CACHE_DIR, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        media_files_deleted += 1
                except Exception as e:
                    logger.warning(f"Erro ao deletar {file_path}: {e}")
        except Exception as e:
            logger.error(f"Erro ao listar cache dir: {e}")

    logger.info(f"Cache limpo: {cache_size} JSON items, {media_files_deleted} files")
    return jsonify({
        "status": "success",
        "message": "Cache limpo com sucesso",
        "json_cache_cleared": cache_size,
        "media_files_deleted": media_files_deleted
    }), 200

@app.route('/api/instagram/cache-status', methods=['GET'])
def cache_status():
    """Mostra status do cache"""
    cache_keys = list(api_cache.keys())

    media_files = []
    media_total_size = 0
    if os.path.exists(MEDIA_CACHE_DIR):
        try:
            for filename in os.listdir(MEDIA_CACHE_DIR):
                file_path = os.path.join(MEDIA_CACHE_DIR, filename)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    age_seconds = time.time() - os.path.getmtime(file_path)
                    media_files.append({
                        "filename": filename,
                        "size_bytes": size,
                        "age_seconds": int(age_seconds),
                        "is_fresh": age_seconds <= MEDIA_CACHE_TTL_SECONDS
                    })
                    media_total_size += size
        except Exception as e:
            logger.error(f"Erro ao listar cache: {e}")

    return jsonify({
        "json_cache": {
            "keys": cache_keys,
            "count": len(cache_keys),
            "ttl_seconds": CACHE_DURATION_SECONDS
        },
        "media_cache": {
            "files_count": len(media_files),
            "total_size_bytes": media_total_size,
            "total_size_mb": round(media_total_size / (1024 * 1024), 2),
            "ttl_seconds": MEDIA_CACHE_TTL_SECONDS,
            "max_size_mb": MEDIA_CACHE_MAX_BYTES / (1024 * 1024),
            "files": media_files[:10]
        }
    }), 200

@app.route('/api/instagram/debug', methods=['GET'])
def debug_info():
    """
    Endpoint para debugging. Mostra:
    - Status do token
    - Tenta chamar IG API
    - Mostra cache status
    - Tenta buscar um media_id específico
    """
    media_id = request.args.get('id', '').strip()
    kind = request.args.get('kind', 'image').strip()

    debug = {
        "timestamp": time.time(),
        "token_configured": bool(ACCESS_TOKEN),
        "token_length": len(ACCESS_TOKEN) if ACCESS_TOKEN else 0,
        "graph_api_url": GRAPH_API_URL,
        "cache_dir": MEDIA_CACHE_DIR,
        "cache_dir_exists": os.path.exists(MEDIA_CACHE_DIR),
        "cache_dir_writable": os.access(MEDIA_CACHE_DIR, os.W_OK) if os.path.exists(MEDIA_CACHE_DIR) else False,
    }

    # Testar conexão com IG
    if ACCESS_TOKEN:
        try:
            r = requests.get(
                f"{GRAPH_API_URL}/me",
                params={"fields": "id,username", "access_token": ACCESS_TOKEN},
                timeout=10
            )
            if r.status_code == 200:
                debug["instagram_connection"] = "✓ OK"
                debug["username"] = r.json().get("username")
            else:
                debug["instagram_connection"] = f"✗ Status {r.status_code}"
                debug["ig_error"] = r.text[:200]
        except Exception as e:
            debug["instagram_connection"] = f"✗ {str(e)}"

    # Se foi passado media_id, tenta debugar especificamente
    if media_id:
        debug["debug_media_id"] = media_id
        debug["debug_kind"] = kind

        try:
            logger.info(f"[DEBUG] Testando media_id={media_id} kind={kind}")

            # 1. Buscar info do IG
            info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
            debug["ig_info"] = {
                "media_type": info.get("media_type"),
                "media_url": info.get("media_url", "")[:100] if info.get("media_url") else None,
                "thumbnail_url": info.get("thumbnail_url", "")[:100] if info.get("thumbnail_url") else None,
            }

            # 2. Selecionar URL
            src = _pick_src_by_kind(info, kind)
            debug["selected_url"] = src[:100] if src else None

            # 3. Testar download
            if src:
                try:
                    r = requests.get(src, stream=True, timeout=10)
                    debug["download_status"] = r.status_code
                    debug["download_content_type"] = r.headers.get("Content-Type")
                    debug["download_content_length"] = r.headers.get("Content-Length")
                except Exception as e:
                    debug["download_error"] = str(e)

            # 4. Testar cache
            try:
                file_path, ct = ensure_media_cached(media_id, kind)
                debug["cache_result"] = {
                    "file_path": file_path,
                    "file_exists": os.path.exists(file_path) if file_path else False,
                    "file_size": os.path.getsize(file_path) if file_path and os.path.exists(file_path) else None,
                    "content_type": ct
                }
            except Exception as e:
                debug["cache_error"] = str(e)

        except Exception as e:
            debug["test_error"] = str(e)
            import traceback
            debug["traceback"] = traceback.format_exc()

    return jsonify(debug), 200

@app.route('/api/instagram/url-examples', methods=['GET'])
def url_examples():
    """
    Mostra exemplos de URLs corretas para usar no frontend.

    ✓ Use a primeira opção (mais simples)
    ⚠ Evite a segunda opção (parsing complexo)
    """
    media_id = request.args.get('id', '17886774234352278')
    kind = request.args.get('kind', 'image')

    from urllib.parse import quote
    inner_url = f"/api/instagram/media_proxy?id={media_id}&kind={kind}"
    encoded_inner = quote(inner_url, safe='')

    return jsonify({
        "media_id": media_id,
        "kind": kind,
        "examples": {
            "✓ RECOMENDADO_1": {
                "description": "Chama diretamente media_proxy (mais rápido)",
                "url": f"/api/instagram/media_proxy?id={media_id}&kind={kind}",
                "use_case": "Use em <img src=\"...\" /> tags"
            },
            "✓ RECOMENDADO_2": {
                "description": "Via proxy-image com URL encoding correto",
                "url": f"/api/instagram/proxy-image?url={encoded_inner}",
                "use_case": "Use se precisar passar por proxy-image"
            },
            "❌ NÃO RECOMENDADO": {
                "description": "Dupla interrogação (causa parsing incorreto)",
                "url": f"/api/instagram/proxy-image?url=/api/instagram/media_proxy?id={media_id}&kind={kind}",
                "problem": "O ? interno quebra o parsing de query strings"
            }
        }
    }), 200

# =========================================
# CLI / Main
# =========================================
def cli_warmup(limit: int, force: bool):
    """Pré-cacheia posts (opcional)"""
    try:
        logger.info("WARMUP: Iniciando...")
        data = ig_get("me/media", "id,media_type,thumbnail_url")
        count = 0
        for item in (data.get("data") or []):
            mid = item.get("id")
            if not mid:
                continue
            logger.info(f"  Cacheando: {mid}")
            ensure_media_cached(mid, "image")
            time.sleep(WARMUP_SLEEP_SECONDS)
            count += 1
            if count >= limit:
                break
        logger.info(f"WARMUP => cached={count} items")
    except Exception as e:
        logger.error(f"WARMUP ERROR: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Instagram API proxy com cache")
    parser.add_argument('--warmup', action='store_true', help='Pré-cachear posts')
    parser.add_argument('--limit', type=int, default=20, help='Limite de items para warmup')
    parser.add_argument('--port', type=int, default=8080, help='Porta')
    args = parser.parse_args()

    if args.warmup:
        cli_warmup(limit=args.limit, force=False)
    else:
        logger.info(f"Starting Instagram API proxy on port {args.port}")
        logger.info(f"Cache dir: {MEDIA_CACHE_DIR}")
        logger.info(f"Request timeout: {REQUEST_TIMEOUT}s")
        app.run(host='0.0.0.0', port=args.port, debug=False)