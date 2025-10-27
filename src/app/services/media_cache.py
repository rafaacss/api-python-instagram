# services/media_cache.py
import os, time, mimetypes, re
from flask import Response, request, current_app, abort
from .http import get
from .instagram import ig_get

# ---------- helpers de content-type/extension ----------
_MP4_FTYP = b"ftyp"
_JPEG = b"\xFF\xD8\xFF"
_PNG  = b"\x89PNG\r\n\x1a\n"
_WEBP = b"RIFF"  # + "WEBP" no offset 8
_GIF  = b"GIF8"

def _ext_from_content_type(ct: str) -> str:
    if not ct:
        return ''
    for k, ext in [('jpeg','.jpg'), ('png','.png'), ('gif','.gif'),
                   ('webp','.webp'), ('mp4','.mp4'), ('mpeg','.mpg')]:
        if k in ct.lower():
            return ext
    return mimetypes.guess_extension(ct) or ''

def _sniff_ext_ct(path: str, ct_header: str | None) -> tuple[str, str]:
    ct = (ct_header or '').lower()
    if ct and ct != 'application/octet-stream':
        return _ext_from_content_type(ct), ct

    with open(path, 'rb') as f:
        head = f.read(16)

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
    except Exception:
        pass

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
    with open(tmp_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=1024*64):
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
    d = current_app.config['MEDIA_CACHE_DIR']
    for name in os.listdir(d):
        if name.startswith(media_id + "."):
            try:
                os.remove(os.path.join(d, name))
            except Exception:
                pass

# ---------- download + normalização ----------
def ensure_media_cached(media_id: str, variant: str = "media", explicit_src: str | None = None) -> tuple[str, str]:
    file_path, meta_path = _cache_paths(media_id, variant)
    if os.path.exists(file_path) and _is_cache_fresh(file_path):
        return file_path, _read_meta(meta_path)

    if explicit_src:
        src = explicit_src
    else:
        info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
        src = info.get("media_url") if variant == "media" else info.get("thumbnail_url")
        if not src:
            src = info.get("media_url") or info.get("thumbnail_url")
    if not src:
        return '', ''

    cdn = get(src, timeout=20, stream=True)
    ct_header = cdn.headers.get('Content-Type', 'application/octet-stream')

    file_path, meta_path = _cache_paths(media_id, variant, ct_header)
    saved = _save_stream_to_file(cdn, file_path, current_app.config['MEDIA_CACHE_MAX_BYTES'])
    if not saved:
        return '', ''

    # Sniff + corrigir extensão e Content-Type
    desired_ext, sniff_ct = _sniff_ext_ct(saved, ct_header)
    fixed_path = _ensure_correct_extension(saved, desired_ext)
    final_ct = sniff_ct or ct_header or 'application/octet-stream'

    _write_meta(meta_path, final_ct)
    os.utime(fixed_path, None)
    return fixed_path, final_ct

# ---------- servir range ----------
def _guess_content_type(path: str, provided: str | None) -> str:
    ct = (provided or "").strip().lower()
    if not ct or ct == "application/octet-stream":
        ct = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if ct == "application/octet-stream" and path.lower().endswith(".mp4"):
        ct = "video/mp4"
    return ct

def serve_file_with_range(path: str, content_type: str | None = None):
    if not os.path.exists(path):
        abort(404)

    file_size = os.path.getsize(path)
    range_header = request.headers.get("Range", "")
    ct = _guess_content_type(path, content_type)

    if not range_header:
        with open(path, "rb") as f:
            data = f.read()
        resp = Response(data, status=200, mimetype=ct)
        resp.headers["Content-Length"] = str(file_size)
        resp.headers["Accept-Ranges"] = "bytes"
        return resp

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
    except Exception:
        resp = Response(status=416)
        resp.headers["Content-Range"] = f"bytes */{file_size}"
        return resp

    with open(path, "rb") as f:
        f.seek(start)
        chunk = f.read(length)

    resp = Response(chunk, status=206, mimetype=ct)
    resp.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    resp.headers["Accept-Ranges"] = "bytes"
    resp.headers["Content-Length"] = str(length)
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp

# ---------- limpeza total ----------
def clear_media_cache_all():
    d = current_app.config['MEDIA_CACHE_DIR']
    if not d or not os.path.isdir(d):
        return {"removed": 0}
    removed = 0
    for name in os.listdir(d):
        try:
            os.remove(os.path.join(d, name))
            removed += 1
        except Exception:
            pass
    return {"removed": removed}
