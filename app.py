import os
import requests
from flask import Flask, jsonify, request, send_file, Response, send_from_directory
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()
app = Flask(__name__, static_folder='static')
CORS(app)

ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
USER_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
GRAPH_API_URL = 'https://graph.instagram.com/v22.0'
api_cache = {}
CACHE_DURATION_SECONDS = 300

def get_from_cache(key):
    return api_cache.get(key)

def set_in_cache(key, data):
    api_cache[key] = data

def fetch_user_profile():
    cache_key = f"profile_{USER_ID}"
    cached = get_from_cache(cache_key)

    if cached:
        return cached["payload"]

    params = {
        "fields": "id,name,username,biography,followers_count,follows_count,media_count,account_type,profile_picture_url",
        "access_token": ACCESS_TOKEN
    }
    url = f"{GRAPH_API_URL}/me"
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    payload = {
        "username": data.get("username"),
        # Foto de perfil NÃO disponível na Graph API. Substitua abaixo por uma URL fixa se quiser.
        "profilePictureUrl": data.get("profile_picture_url"),  # Placeholder
        "fullName": data.get("name"),
        "isVerified": True,
        "biography": data.get("biography"),
        "postsCount": data.get("media_count"),
        "followersCount": data.get("followers_count"),
        "followingCount": data.get("follows_count")
    }
    set_in_cache(cache_key, {"payload": payload})
    return payload


@app.route('/api/instagram/user_profile', methods=['GET'])
def get_user_profile():
    try:
        profile = fetch_user_profile()
        return jsonify({
            "code": 200,
            "payload": profile,
            "message": ""
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/instagram/posts', methods=['GET'])
def get_user_posts():
    username = request.args.get('username', 'me')
    cache_key = f"posts_{username}"
    cached_data = get_from_cache(cache_key)
    if cached_data:
        print(f"Servindo posts de '{username}' do cache")
        return jsonify(cached_data)

    if not ACCESS_TOKEN:
        return jsonify({"error": "Access Token não configurado no backend"}), 500

    # Busca as infos do perfil UMA VEZ só!
    try:
        user_info = fetch_user_profile()
    except Exception as e:
        return jsonify({"error": "Falha ao buscar perfil: " + str(e)}), 500

    posts_endpoint = f"{GRAPH_API_URL}/{USER_ID}/media"
    params = {
        "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username,children{media_type,media_url,thumbnail_url},comments_count,like_count",
        "access_token": ACCESS_TOKEN,
        "limit": 20
    }

    try:
        response = requests.get(posts_endpoint, params=params)
        response.raise_for_status()
        api_data = response.json()
        formatted_posts = []

        width, height = 1080.0, 1920.0

        for post in api_data.get("data", []):
            # Preenche o author com todas infos do perfil
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
            if post.get("media_type") == "IMAGE":
                media_items.append({
                    "type": "image",
                    "url": post.get("media_url"),
                    "cover": {
                        "thumbnail": {
                            "url": post.get("media_url"),
                            "width": width,
                            "height": height
                        },
                        "standard": None,
                        "original": None
                    },
                    "id": None
                })
            elif post.get("media_type") == "VIDEO":
                media_items.append({
                    "type": "video",
                    "url": post.get("media_url"),
                    "cover": {
                        "thumbnail": {
                            "url": post.get("thumbnail_url", post.get("media_url")),
                            "width": width,
                            "height": height
                        },
                        "standard": None,
                        "original": None
                    },
                    "id": None
                })
            elif post.get("media_type") == "CAROUSEL_ALBUM":
                children = post.get("children", {}).get("data", [])
                for child in children:
                    m_type = child.get("media_type")
                    url = child.get("media_url")
                    thumb = child.get("thumbnail_url", url)
                    media_items.append({
                        "type": m_type.lower(),
                        "url": url,
                        "cover": {
                            "thumbnail": {
                                "url": thumb,
                                "width": width,
                                "height": height
                            },
                            "standard": None,
                            "original": None
                        },
                        "id": None
                    })

            formatted_post = {
                "vendorId": post.get("id"),
                "type": post.get("media_type", "").lower().replace("_album", ""),
                "link": post.get("permalink"),
                "publishedAt": post.get("timestamp"),
                "author": author,
                "media": media_items,
                "comments": [],
                "caption": post.get("caption"),
                "commentsCount": post.get("comments_count", 0),
                "likesCount": post.get("like_count", 0),
                "extra": {"platform": "instagram"},
                "isPinned": None
            }
            formatted_posts.append(formatted_post)

        final_response = {
            "code": 200,
            "payload": formatted_posts
        }
        set_in_cache(cache_key, final_response)
        print(f"Posts de '{username}' buscados da API e cacheados")
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

@app.route('/api/instagram/proxy-image')
def proxy_image():
    url = request.args.get('url')
    if not url:
        return Response('Missing URL', status=400)
    # Segurança: permite apenas imagens do domínio Instagram CDN
    if not url.startswith('https://scontent') and not url.startswith('https://instagram'):
        return Response('Blocked domain', status=403)
    try:
        r = requests.get(url, stream=True, timeout=8)
        r.raise_for_status()
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        # Evita download, só mostra imagem
        return Response(r.content, content_type=content_type)
    except Exception as e:
        return Response(f'Error: {e}', status=500)

if __name__ == '__main__':
    app.run(debug=True, port=8080)
