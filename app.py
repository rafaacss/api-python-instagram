import os
import time
import requests
from flask import Flask, jsonify, request, send_file, Response, send_from_directory, abort
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()
app = Flask(__name__, static_folder='static')
CORS(app)

# ----------------------------- #
# Config
# ----------------------------- #
ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
USER_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
GRAPH_API_URL = 'https://graph.instagram.com/v22.0'
CACHE_DURATION_SECONDS = int(os.getenv('CACHE_DURATION_SECONDS', '300'))

PLACE_ID = os.getenv('GOOGLE_PLACE_ID')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Cache simples em memória com TTL
api_cache = {}  # key -> {"ts": epoch_seconds, "data": any}


# ----------------------------- #
# Cache helpers (com TTL)
# ----------------------------- #
def get_from_cache(key):
    item = api_cache.get(key)
    if not item:
        return None
    ts = item.get("ts")
    if ts is None or (time.time() - ts) > CACHE_DURATION_SECONDS:
        # expirou
        api_cache.pop(key, None)
        return None
    return item.get("data")


def set_in_cache(key, data):
    api_cache[key] = {"ts": time.time(), "data": data}


# ----------------------------- #
# Instagram helpers
# ----------------------------- #
def ig_get(path_or_full_url, params):
    """Wrapper para GET na Graph API do Instagram com token e timeout padronizados."""
    if path_or_full_url.startswith("http"):
        url = path_or_full_url
    else:
        url = f"{GRAPH_API_URL.rstrip('/')}/{path_or_full_url.lstrip('/')}"
    base_params = {"access_token": ACCESS_TOKEN}
    base_params.update(params or {})
    r = requests.get(url, params=base_params, timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_user_profile():
    """Busca e cacheia perfil do usuário; retorna payload formatado para o frontend."""
    cache_key = f"profile_{USER_ID}"
    cached = get_from_cache(cache_key)
    if cached:
        return cached

    # Nota: Graph API /me retorna dados limitados para IG Business/Creator conectados.
    params = {
        "fields": "id,username,biography,followers_count,follows_count,media_count,account_type",
    }
    data = ig_get("me", params=params)

    payload = {
        "username": data.get("username"),
        # A foto de perfil muitas vezes não é retornada pela Graph API IG Business.
        # Se quiser algo fixo, ajuste aqui:
        "profilePictureUrl": None,
        "fullName": None,  # "name" não é garantido para IG Business
        "isVerified": True,  # se precisar, ajuste de acordo com sua lógica
        "biography": data.get("biography"),
        "postsCount": data.get("media_count"),
        "followersCount": data.get("followers_count"),
        "followingCount": data.get("follows_count")
    }
    set_in_cache(cache_key, payload)
    return payload


def fetch_media_meta(media_id, fields="media_type,media_url,thumbnail_url,permalink"):
    """Busca metadados de uma mídia pelo ID (gera URLs frescas)."""
    return ig_get(media_id, params={"fields": fields})


# ----------------------------- #
# Rotas Instagram
# ----------------------------- #
@app.route('/api/instagram/user_profile', methods=['GET'])
def get_user_profile():
    try:
        profile = fetch_user_profile()
        return jsonify({"code": 200, "payload": profile, "message": ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/instagram/posts', methods=['GET'])
def get_user_posts():
    """
    Retorna a lista de posts, mas ***sem*** URLs de mídia expiráveis.
    Em vez disso, devolve IDs (do post e dos filhos do carrossel).
    O front deve buscar a URL fresca via:
      - /api/instagram/media_proxy?id=<MEDIA_ID>  (recomendado)
      - ou /api/instagram/media_url?id=<MEDIA_ID>
    """
    username = request.args.get('username', 'me')
    cache_key = f"posts_{username}"
    cached_data = get_from_cache(cache_key)
    if cached_data:
        print(f"Servindo posts de '{username}' do cache (TTL {CACHE_DURATION_SECONDS}s)")
        return jsonify(cached_data)

    if not ACCESS_TOKEN:
        return jsonify({"error": "Access Token não configurado no backend"}), 500

    try:
        user_info = fetch_user_profile()
    except Exception as e:
        return jsonify({"error": "Falha ao buscar perfil: " + str(e)}), 500

    posts_endpoint = f"{USER_ID}/media"
    params = {
        # Importante: pedimos children{id,media_type} apenas; não pedimos media_url para não guardar coisa que expira
        "fields": "id,caption,media_type,permalink,timestamp,username,children{id,media_type},comments_count,like_count",
        "limit": 20
    }

    try:
        api_data = ig_get(posts_endpoint, params=params)
        formatted_posts = []

        for post in api_data.get("data", []):
            author = {
                "username": user_info.get("username"),
                "url": None,
                "profilePictureUrl": user_info.get("profilePictureUrl"),
                "isVerifiedProfile": user_info.get("isVerified"),
                "name": user_info.get("fullName"),
                "biography": user_info.get("biography"),
                "postsCount": user_info.get("postsCount"),
                "followersCount": user_info.get("followersCount"),
                "followingCount": user_info.get("followingCount")
            }

            media_items = []
            ptype = (post.get("media_type") or "").upper()

            if ptype in ("IMAGE", "VIDEO"):
                media_items.append({
                    "type": ptype.lower(),  # "image" | "video"
                    "id": post.get("id")    # o próprio post é a mídia
                })

            elif ptype == "CAROUSEL_ALBUM":
                children = (post.get("children") or {}).get("data", [])
                for child in children:
                    ctype = (child.get("media_type") or "").lower()
                    media_items.append({
                        "type": ctype,       # "image" | "video"
                        "id": child.get("id")
                    })

            formatted_post = {
                "vendorId": post.get("id"),
                "type": ptype.lower().replace("_album", ""),
                "link": post.get("permalink"),
                "publishedAt": post.get("timestamp"),
                "author": author,
                "media": media_items,   # << só IDs; sem URLs que expiram
                "comments": [],
                "caption": post.get("caption"),
                "commentsCount": post.get("comments_count", 0),
                "likesCount": post.get("like_count", 0),
                "extra": {"platform": "instagram"},
                "isPinned": None
            }
            formatted_posts.append(formatted_post)

        final_response = {"code": 200, "payload": formatted_posts}
        set_in_cache(cache_key, final_response)
        print(f"Posts de '{username}' buscados da API e cacheados (TTL {CACHE_DURATION_SECONDS}s)")
        return jsonify(final_response)

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar posts do Instagram: {e}")
        error_payload = {"error": str(e)}
        if e.response is not None:
            try:
                error_payload["details"] = e.response.json()
            except ValueError:
                error_payload["details"] = e.response.text
        return jsonify(error_payload), getattr(e.response, 'status_code', 500)


@app.route('/api/instagram/media_url', methods=['GET'])
def get_media_url():
    """
    Dado um media_id, retorna media_url/thumbnail_url Frescos.
    Uso: GET /api/instagram/media_url?id=<MEDIA_ID>
    """
    media_id = request.args.get('id')
    if not media_id:
        return jsonify({"error": "Parâmetro 'id' é obrigatório"}), 400

    try:
        info = fetch_media_meta(media_id, fields="media_type,media_url,thumbnail_url,permalink")
        return jsonify({
            "code": 200,
            "payload": {
                "media_type": info.get("media_type"),
                "media_url": info.get("media_url"),
                "thumbnail_url": info.get("thumbnail_url"),
                "permalink": info.get("permalink")
            }
        })
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, 'status_code', 500)
        return jsonify({"error": str(e)}), status


@app.route('/api/instagram/media_proxy', methods=['GET'])
def media_proxy():
    """
    Proxy que aceita um media_id e entrega o binário da mídia com URL sempre válida.
    Uso: <img src="/api/instagram/media_proxy?id=<MEDIA_ID>">
    """
    media_id = request.args.get('id')
    if not media_id:
        return Response('Missing id', status=400)

    try:
        info = fetch_media_meta(media_id, fields="media_type,media_url,thumbnail_url")
        src = info.get("media_url") or info.get("thumbnail_url")
        if not src:
            return Response('No media_url available', status=502)

        cdn = requests.get(src, stream=True, timeout=10)
        cdn.raise_for_status()
        content_type = cdn.headers.get('Content-Type', 'application/octet-stream')
        return Response(cdn.content, content_type=content_type)
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, 'status_code', 500)
        return Response(f'Error: {e}', status=status)
    except Exception as e:
        return Response(f'Error: {e}', status=500)


@app.route('/api/instagram/proxy-image', methods=['GET'])
def proxy_image_legacy():
    """
    LEGADO: proxy por URL direta (ainda funciona, mas a URL pode expirar).
    Prefira /api/instagram/media_proxy?id=...
    """
    url = request.args.get('url')
    if not url:
        return Response('Missing URL', status=400)
    # Segurança simples: só permitir domínios instagram/scontent
    if not (url.startswith('https://scontent') or url.startswith('https://instagram')):
        return Response('Blocked domain', status=403)
    try:
        r = requests.get(url, stream=True, timeout=8)
        r.raise_for_status()
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        return Response(r.content, content_type=content_type)
    except Exception as e:
        return Response(f'Error: {e}', status=500)


# ----------------------------- #
# Google reviews
# ----------------------------- #
@app.route('/api/google/reviews')
def google_reviews():
    try:
        reviews = get_google_reviews()
        return jsonify({"code": 200, "payload": reviews})
    except Exception as e:
        return jsonify({"code": 500, "error": str(e)})


def get_google_reviews():
    if not PLACE_ID or not GOOGLE_API_KEY:
        return []
    url = (
        "https://maps.googleapis.com/maps/api/place/details/json"
        f"?place_id={PLACE_ID}"
        f"&fields=reviews,rating,user_ratings_total,name"
        f"&key={GOOGLE_API_KEY}"
    )
    response = requests.get(url, timeout=10)
    data = response.json()
    if "result" in data and "reviews" in data["result"]:
        return data["result"]["reviews"]
    else:
        return []


# ----------------------------- #
# Static & util
# ----------------------------- #
ALLOWED_EXTENSIONS = {'.json', '.js'}

def allowed_file(filename):
    ext = os.path.splitext(filename)[1]
    return ext in ALLOWED_EXTENSIONS


@app.route('/static/instagram/<path:filename>')
def serve_instagram_static(filename):
    return send_from_directory('static/instagram', filename)


@app.route('/static/instagramm/<filename>')
def serve_static_instagram(filename):
    if not allowed_file(filename):
        abort(404)
    filepath = os.path.join('static', 'instagram', filename)
    if not os.path.isfile(filepath):
        abort(404)

    # Serve o arquivo correto com o mimetype apropriado
    ext = os.path.splitext(filename)[1]
    if ext == '.json':
        mimetype = 'application/json'
    elif ext == '.js':
        mimetype = 'application/javascript'
    else:
        mimetype = 'application/octet-stream'  # fallback seguro

    with open(filepath, 'rb') as f:
        content = f.read()
    return Response(content, mimetype=mimetype)


# ----------------------------- #
# Main
# ----------------------------- #
if __name__ == '__main__':
    app.run(debug=True, port=8080)
