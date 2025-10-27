import time
import logging
from flask import current_app
from .instagram import ig_get_url
from .media_cache import ensure_media_cached, drop_media_cache

logger = logging.getLogger(__name__)


def collect_media_ids(limit_posts: int = 20) -> list[str]:
    s = current_app.config
    ids, got = [], 0
    fields = "id,media_type,children{id,media_type}"
    url = f"{s['GRAPH_API_URL']}/{s['USER_ID']}/media?fields={fields}&limit=25&access_token={s['ACCESS_TOKEN']}"

    logger.info(f"Coletando media IDs (limite: {limit_posts})")

    try:
        while url and got < limit_posts:
            logger.info(f"Buscando página: {url[:80]}...")
            data = ig_get_url(url)

            for post in data.get("data", []):
                if got >= limit_posts:
                    break
                ptype = (post.get("media_type") or "").upper()
                logger.info(f"Post: type={ptype}, id={post.get('id')}")

                if ptype in ("IMAGE", "VIDEO"):
                    ids.append(post.get("id"))
                    got += 1
                elif ptype == "CAROUSEL_ALBUM":
                    for child in (post.get("children") or {}).get("data", []):
                        ids.append(child.get("id"))
                        got += 1
                        if got >= limit_posts:
                            break

            url = (data.get("paging") or {}).get("next")
            logger.info(f"Próxima página disponível: {bool(url)}")
    except Exception as e:
        logger.error(f"Erro ao coletar media IDs: {e}", exc_info=True)

    # dedup
    seen, uniq = set(), []
    for mid in ids:
        if mid and mid not in seen:
            seen.add(mid)
            uniq.append(mid)

    logger.info(f"Total de media IDs únicos coletados: {len(uniq)}")
    return uniq


def warmup(limit_posts: int = 20, force: bool = False):
    s = current_app.config
    logger.info(f"Iniciando warmup: limit_posts={limit_posts}, force={force}")

    mids = collect_media_ids(limit_posts)
    ok = sk = fa = 0
    details = []

    for mid in mids:
        try:
            logger.info(f"Processando media: {mid}")
            if force:
                logger.info(f"Force=true, removendo cache anterior: {mid}")
                drop_media_cache(mid)

            file_path, ct = ensure_media_cached(mid)
            if file_path:
                ok += 1
                details.append({"id": mid, "status": "cached", "path": file_path})
                logger.info(f"OK: {mid} -> {file_path}")
            else:
                sk += 1
                details.append({"id": mid, "status": "skipped"})
                logger.warning(f"SKIPPED: {mid}")
        except Exception as e:
            fa += 1
            details.append({"id": mid, "status": "failed", "error": str(e)})
            logger.error(f"FAILED: {mid} -> {e}")

        time.sleep(s['WARMUP_SLEEP_SECONDS'])

    result = {
        "posts_scanned": limit_posts,
        "media_found": len(mids),
        "cached": ok,
        "skipped": sk,
        "failed": fa,
        "details": details
    }

    logger.info(f"Warmup finalizado: {result}")
    return result