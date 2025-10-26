import time
from flask import current_app
from .instagram import ig_get_url
from .media_cache import ensure_media_cached, drop_media_cache

def collect_media_ids(limit_posts: int = 20) -> list[str]:
    s = current_app.config
    ids, got = [], 0
    fields = "id,media_type,children{id,media_type}"
    url = f"{s['GRAPH_API_URL']}/{s['USER_ID']}/media?fields={fields}&limit=25&access_token={s['ACCESS_TOKEN']}"
    try:
        while url and got < limit_posts:
            data = ig_get_url(url)
            for post in data.get("data", []):
                if got >= limit_posts: break
                ptype = (post.get("media_type") or "").upper()
                if ptype in ("IMAGE","VIDEO"):
                    ids.append(post.get("id"))
                elif ptype == "CAROUSEL_ALBUM":
                    for child in (post.get("children") or {}).get("data", []):
                        ids.append(child.get("id"))
                got += 1
            url = (data.get("paging") or {}).get("next")
    except Exception:
        pass
    # dedup
    seen, uniq = set(), []
    for mid in ids:
        if mid and mid not in seen: seen.add(mid); uniq.append(mid)
    return uniq

def warmup(limit_posts: int = 20, force: bool = False):
    s = current_app.config
    mids = collect_media_ids(limit_posts)
    ok=sk=fa=0; details=[]
    for mid in mids:
        try:
            if force: drop_media_cache(mid)
            file_path, ct = ensure_media_cached(mid)
            if file_path: ok+=1; details.append({"id": mid, "status":"cached","path":file_path})
            else: sk+=1; details.append({"id": mid, "status":"skipped"})
        except Exception as e:
            fa+=1; details.append({"id": mid, "status":"failed", "error": str(e)})
        time.sleep(s['WARMUP_SLEEP_SECONDS'])
    return {"posts_scanned": limit_posts, "media_found": len(mids), "cached": ok, "skipped": sk, "failed": fa, "details": details}
