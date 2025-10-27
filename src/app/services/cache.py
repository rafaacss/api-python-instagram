import time

_api_cache = {}  # key -> {"data":..., "ts":...}

def get_from_cache(key, ttl_seconds):
    item = _api_cache.get(key)
    if not item:
        return None
    if (time.time() - item["ts"]) > ttl_seconds:
        _api_cache.pop(key, None)
        return None
    return item["data"]

def set_in_cache(key, data):
    _api_cache[key] = {"data": data, "ts": time.time()}

def clear_memory_cache():
    _api_cache.clear()
    return True