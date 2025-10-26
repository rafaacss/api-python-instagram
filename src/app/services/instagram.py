from flask import current_app
from .http import get
from .cache import get_from_cache, set_in_cache

def ig_get(path_or_id: str, fields: str, extra: dict | None = None):
    s = current_app.config
    url = f"{s['GRAPH_API_URL'].rstrip('/')}/{path_or_id.lstrip('/')}"
    params = {"fields": fields, "access_token": s['ACCESS_TOKEN']}
    if extra:
        params.update(extra)
    return get(url, params=params).json()

def ig_get_url(full_url: str):
    return get(full_url).json()

def fetch_user_profile():
    s = current_app.config
    cache_key = f"profile_{s['USER_ID']}"
    cached = get_from_cache(cache_key, s['CACHE_DURATION_SECONDS'])
    if cached:
        return cached

    fields = "id,username,biography,followers_count,follows_count,media_count,account_type"
    data = ig_get("me", fields)
    payload = {
        "username": data.get("username"),
        "profilePictureUrl": None,
        "fullName": None,
        "isVerified": True,
        "biography": data.get("biography"),
        "postsCount": data.get("media_count"),
        "followersCount": data.get("followers_count"),
        "followingCount": data.get("follows_count"),
    }
    set_in_cache(cache_key, payload)
    return payload
