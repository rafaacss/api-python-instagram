import requests

DEFAULT_TIMEOUT = 10

def get(url, *, params=None, timeout=DEFAULT_TIMEOUT, stream=False):
    r = requests.get(url, params=params, timeout=timeout, stream=stream)
    r.raise_for_status()
    return r
