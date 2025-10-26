import os
from dotenv import load_dotenv
load_dotenv()

class Settings:
    ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN', '')
    USER_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID', '')
    GRAPH_API_URL = os.getenv('GRAPH_API_URL', 'https://graph.instagram.com/v22.0')

    API_BASE_URL = os.getenv('API_BASE_URL', '').rstrip('/')
    if not API_BASE_URL:
        raise RuntimeError("Env var API_BASE_URL não definida")

    CACHE_DURATION_SECONDS = int(os.getenv('CACHE_DURATION_SECONDS', '3600'))
    PLACE_ID = os.getenv('GOOGLE_PLACE_ID', '')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')

    MEDIA_CACHE_DIR = os.getenv('MEDIA_CACHE_DIR', os.path.join(os.getcwd(), 'cache', 'instagram'))
    MEDIA_CACHE_TTL_SECONDS = int(os.getenv('MEDIA_CACHE_TTL_SECONDS', '3600'))
    MEDIA_CACHE_MAX_BYTES = int(os.getenv('MEDIA_CACHE_MAX_BYTES', str(25 * 1024 * 1024)))
    WARMUP_TOKEN = os.getenv('WARMUP_TOKEN', '')
    WARMUP_SLEEP_SECONDS = float(os.getenv('WARMUP_SLEEP_SECONDS', '0.25'))
