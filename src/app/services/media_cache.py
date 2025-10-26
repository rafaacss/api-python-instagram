import os, time, mimetypes
from flask import Response, request, current_app
from .http import get
from .instagram import ig_get

def _ext_from_content_type(ct: str) -> str:
    if not ct: return ''
    for k, ext in [('jpeg','.jpg'), ('png','.png'), ('gif','.gif'),
                   ('webp','.webp'), ('mp4','.mp4'), ('mpeg','.mpg')]:
        if k in ct: return ext
    return mimetypes.guess_extension(ct) or ''

def _cache_paths(media_id: str, content_type: str | None = None):
    d = current_app.config['MEDIA_CACHE_DIR']
    for name in os.listdir(d):
        if name.startswith(media_id + "."):
            p = os.path.join(d, name)
            meta = os.path.join(d, f"{media_id}.meta")
            return p, meta
    ext = _ext_from_content_type(content_type) if content_type else '.bin'
    return (os.path.join(d, f"{media_id}{ext}"),
            os.path.join(d, f"{media_id}.meta"))

def _write_meta(meta_path: str, content_type: str):
    try:
        with open(meta_path, 'w') as f: f.write(content_type or 'application/octet-stream')
    except Exception: pass

def _read_meta(meta_path: str) -> str:
    try:
        with open(meta_path, 'r') as f: return f.read().strip()
    except Exception: return 'application/octet-stream'

def _is_cache_fresh(path: str) -> bool:
    if not os.path.exists(path): return False
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
                    f.close(); os.remove(tmp_path); return ''
                f.write(chunk)
    if os.path.exists(dst_path): os.remove(dst_path)
    os.rename(tmp_path, dst_path)
    return dst_path

def drop_media_cache(media_id: str):
    d = current_app.config['MEDIA_CACHE_DIR']
    for name in os.listdir(d):
        if name.startswith(media_id + "."):
            try: os.remove(os.path.join(d, name))
            except Exception: pass

def ensure_media_cached(media_id: str) -> tuple[str, str]:
    file_path, meta_path = _cache_paths(media_id)
    if os.path.exists(file_path) and _is_cache_fresh(file_path):
        return file_path, _read_meta(meta_path)

    info = ig_get(media_id, fields="media_type,media_url,thumbnail_url")
    src = info.get("media_url") or info.get("thumbnail_url")
    if not src: return '', ''

    cdn = get(src, timeout=20, stream=True)
    ct = cdn.headers.get('Content-Type', 'application/octet-stream')
    file_path, meta_path = _cache_paths(media_id, ct)
    saved = _save_stream_to_file(cdn, file_path, current_app.config['MEDIA_CACHE_MAX_BYTES'])
    if saved:
        _write_meta(meta_path, ct)
        os.utime(saved, None)
        return saved, ct
    return '', ''

def serve_file_with_range(path: str, content_type: str):
    file_size = os.path.getsize(path)
    range_header = request.headers.get('Range')
    if not range_header:
        with open(path, 'rb') as f: data = f.read()
        resp = Response(data, mimetype=content_type)
        resp.headers['Content-Length'] = str(file_size)
        resp.headers['Accept-Ranges'] = 'bytes'
        return resp
    try:
        units, rng = range_header.split('=')
        start_str, end_str = rng.split('-')
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
        end = min(end, file_size - 1)
        if units != 'bytes' or start > end or start < 0:
            raise ValueError
    except Exception:
        return Response(status=416)
    length = end - start + 1
    with open(path, 'rb') as f:
        f.seek(start); chunk = f.read(length)
    resp = Response(chunk, status=206, mimetype=content_type)
    resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    resp.headers['Accept-Ranges'] = 'bytes'
    resp.headers['Content-Length'] = str(length)
    return resp
