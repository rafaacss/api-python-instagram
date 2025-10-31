# services/media_cache.py
import os, time, mimetypes, re, logging
from flask import Response, request, current_app, abort, send_file
from .http import get
from .instagram import ig_get

logger = logging.getLogger(__name__)

# ---------- helpers de content-type/extension ----------
_MP4_FTYP = b"ftyp"
_JPEG = b"\xFF\xD8\xFF"
_PNG = b"\x89PNG\r\n\x1a\n"
_WEBP = b"RIFF"  # + "WEBP" no offset 8
_GIF = b"GIF8"


def _ext_from_content_type(ct: str) -> str:
    if not ct:
        return ''
    for k, ext in [('jpeg', '.jpg'), ('png', '.png'), ('gif', '.gif'),
                   ('webp', '.webp'), ('mp4', '.mp4'), ('mpeg', '.mpg')]:
        if k in ct.lower():
            return ext
    return mimetypes.guess_extension(ct) or ''


def _sniff_ext_ct(path: str, ct_header: str | None) -> tuple[str, str]:
    ct = (ct_header or '').lower()
    if ct and ct != 'application/octet-stream':
        return _ext_from_content_type(ct), ct

    with open(path, 'rb') as f:
        head = f.read(32)  # Aumentado de 16 para detectar melhor MP4

    # MP4: 'ftyp' costuma aparecer em 4..12
    if len(head) >= 12 and _MP4_FTYP in head[4:12]:
        return '.mp4', 'video/mp4'
    if head.startswith(_JPEG):
        return '.jpg', 'image/jpeg'
    if head.startswith(_PNG):
        return '.png', 'image/png'
    if head.startswith(_GIF):
        return '.gif', 'image/gif'
    if head.startswith(_WEBP) and b'WEBP' in head[8:16]:
        return '.webp', 'image/webp'

    guessed = mimetypes.guess_type(path)[0]
    if guessed:
        return _ext_from_content_type(guessed), guessed
    return '', 'application/octet-stream'


def _ensure_correct_extension(path: str, desired_ext: str) -> str:
    if not desired_ext:
        return path
    base, current_ext = os.path.splitext(path)
    if current_ext.lower() == desired_ext.lower():
        return path
    new_path = base + desired_ext
    if os.path.exists(new_path):
        os.remove(new_path)
    os.rename(path, new_path)
    return new_path


# ---------- cache paths ----------
def _cache_paths(media_id: str, variant: str = "media", content_type: str | None = None):
    d = current_app.config['MEDIA_CACHE_DIR']
    base = f"{media_id}.{variant}"
    for name in os.listdir(d):
        if name.startswith(base + "."):
            p = os.path.join(d, name)
            meta = os.path.join(d, f"{base}.meta")
            return p, meta
    ext = _ext_from_content_type(content_type) if content_type else '.bin'
    return (os.path.join(d, f"{base}{ext}"),
            os.path.join(d, f"{base}.meta"))


def _write_meta(meta_path: str, content_type: str):
    try:
        with open(meta_path, 'w') as f:
            f.write(content_type or 'application/octet-stream')
    except Exception as e:
        logger.error(f"Erro ao escrever meta {meta_path}: {e}")


def _read_meta(meta_path: str) -> str:
    try:
        with open(meta_path, 'r') as f:
            return f.read().strip()
    except Exception:
        return 'application/octet-stream'


def _is_cache_fresh(path: str) -> bool:
    if not os.path.exists(path):
        return False
    age = time.time() - os.path.getmtime(path)
    return age <= current_app.config['MEDIA_CACHE_TTL_SECONDS']


def _save_stream_to_file(resp, dst_path: str, max_bytes: int) -> str:
    tmp_path = dst_path + ".tmp"
    total = 0
    try:
        with open(tmp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                if chunk:
                    total += len(chunk)
                    if total > max_bytes:
                        f.close()
                        os.remove(tmp_path)
                        logger.warning(f"Arquivo excedeu tamanho máximo: {dst_path} ({total} > {max_bytes})")
                        return ''
                    f.write(chunk)
        if os.path.exists(dst_path):
            os.remove(dst_path)
        os.rename(tmp_path, dst_path)
        logger.info(f"Arquivo salvo: {dst_path} ({total} bytes)")
        return dst_path
    except Exception as e:
        logger.error(f"Erro ao salvar stream: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return ''


def drop_media_cache(media_id: str):
    d = current_app.config['MEDIA_CACHE_DIR']
    try:
        for name in os.listdir(d):
            if name.startswith(media_id + "."):
                try:
                    os.remove(os.path.join(d, name))
                    logger.info(f"Removido: {name}")
                except Exception as e:
                    logger.error(f"Erro ao remover {name}: {e}")
    except Exception as e:
        logger.error(f"Erro ao limpar cache para {media_id}: {e}")


# ---------- download + normalização ----------
def ensure_media_cached(media_id: str, variant: str = "media", explicit_src: str | None = None) -> tuple[str, str]:
    logger.info(f"ensure_media_cached chamado: media_id={media_id}, variant={variant}")

    file_path, meta_path = _cache_paths(media_id, variant)
    if os.path.exists(file_path) and _is_cache_fresh(file_path):
        ct = _read_meta(meta_path)
        logger.info(f"Cache fresco encontrado: {file_path}")
        return file_path, ct

    if explicit_src:
        src = explicit_src
        logger.info(f"Usando src explícito: {src[:50]}...")
    else:
        try:
            info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
            logger.info(f"Info do Instagram: {info}")
        except Exception as e:
            logger.error(f"Erro ao buscar info do Instagram: {e}")
            return '', ''

        if variant == "thumb":
            src = info.get("thumbnail_url") or info.get("media_url")
        else:
            src = info.get("media_url") or info.get("thumbnail_url")

    if not src:
        logger.warning(f"Nenhuma URL disponível para {media_id}")
        return '', ''

    try:
        logger.info(f"Baixando mídia: {src[:50]}...")
        cdn = get(src, timeout=20, stream=True)
        ct_header = cdn.headers.get('Content-Type', 'application/octet-stream')
        logger.info(f"Content-Type recebido: {ct_header}")

        file_path, meta_path = _cache_paths(media_id, variant, ct_header)
        saved = _save_stream_to_file(cdn, file_path, current_app.config['MEDIA_CACHE_MAX_BYTES'])

        if not saved:
            logger.error(f"Falha ao salvar: {file_path}")
            return '', ''

        # Sniff + corrigir extensão e Content-Type
        desired_ext, sniff_ct = _sniff_ext_ct(saved, ct_header)
        logger.info(f"Detectado: ext={desired_ext}, ct={sniff_ct}")

        fixed_path = _ensure_correct_extension(saved, desired_ext)
        final_ct = sniff_ct or ct_header or 'application/octet-stream'

        _write_meta(meta_path, final_ct)
        os.utime(fixed_path, None)
        logger.info(f"Mídia cacheada com sucesso: {fixed_path}")
        return fixed_path, final_ct
    except Exception as e:
        logger.error(f"Erro ao fazer cache de mídia: {e}", exc_info=True)
        return '', ''


# ---------- servir range ----------
def _guess_content_type(path: str, provided: str | None) -> str:
    ct = (provided or "").strip().lower()

    # Se já temos um content-type válido, use
    if ct and ct not in ("application/octet-stream", ""):
        return ct

    # Tente descobrir pela extensão
    ext = os.path.splitext(path)[1].lower()
    ext_map = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }

    if ext in ext_map:
        return ext_map[ext]

    guessed = mimetypes.guess_type(path)[0]
    return guessed or "application/octet-stream"


def serve_file_with_range(path: str, content_type: str | None = None):
    logger.info(f"serve_file_with_range: {path}, ct={content_type}")

    if not os.path.exists(path):
        logger.error(f"Arquivo não encontrado: {path}")
        abort(404)

    file_size = os.path.getsize(path)
    range_header = request.headers.get("Range", "")
    ct = _guess_content_type(path, content_type)

    logger.info(f"Servindo: {path}, size={file_size}, ct={ct}, range={range_header}")

    if not range_header:
        try:
            with open(path, "rb") as f:
                data = f.read()
            resp = Response(data, status=200, mimetype=ct)
            resp.headers["Content-Length"] = str(file_size)
            resp.headers["Accept-Ranges"] = "bytes"
            resp.headers["Cache-Control"] = "public, max-age=3600"
            return resp
        except Exception as e:
            logger.error(f"Erro ao ler arquivo: {e}")
            abort(500)

    m = re.match(r"bytes=(\d*)-(\d*)$", range_header.strip())
    if not m:
        resp = Response(status=416)
        resp.headers["Content-Range"] = f"bytes */{file_size}"
        return resp

    start_s, end_s = m.groups()

    try:
        if start_s == "" and end_s == "":
            raise ValueError("empty range")

        if start_s == "":  # bytes=-N
            suffix_len = int(end_s)
            if suffix_len <= 0:
                raise ValueError("invalid suffix length")
            start = max(file_size - suffix_len, 0)
            end = file_size - 1
        else:
            start = int(start_s)
            if start >= file_size:
                resp = Response(status=416)
                resp.headers["Content-Range"] = f"bytes */{file_size}"
                return resp
            end = int(end_s) if end_s != "" else file_size - 1

        end = min(end, file_size - 1)
        if start > end or start < 0:
            raise ValueError("invalid range order")

        length = end - start + 1
    except Exception as e:
        logger.error(f"Erro ao processar range: {e}")
        resp = Response(status=416)
        resp.headers["Content-Range"] = f"bytes */{file_size}"
        return resp

    try:
        with open(path, "rb") as f:
            f.seek(start)
            chunk = f.read(length)

        resp = Response(chunk, status=206, mimetype=ct)
        resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        resp.headers["Accept-Ranges"] = "bytes"
        resp.headers["Content-Length"] = str(length)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        logger.info(f"Range enviado: {start}-{end}/{file_size}")
        return resp
    except Exception as e:
        logger.error(f"Erro ao servir range: {e}")
        abort(500)


# ---------- limpeza total ----------
def clear_media_cache_all():
    d = current_app.config['MEDIA_CACHE_DIR']
    if not d or not os.path.isdir(d):
        logger.warning(f"Cache dir não existe ou não é diretório: {d}")
        return {"removed": 0}
    removed = 0
    for name in os.listdir(d):
        try:
            path = os.path.join(d, name)
            os.remove(path)
            removed += 1
            logger.info(f"Removido: {name}")
        except Exception as e:
            logger.error(f"Erro ao remover {name}: {e}")
    logger.info(f"Cache limpo: {removed} arquivos removidos")
    return {"removed": removed}