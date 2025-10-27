"""
Script para testar os endpoints da aplicação
Uso: python test_endpoints.py
"""

import requests
import json
from urllib.parse import urljoin

# Configure a URL base da sua aplicação
BASE_URL = "http://localhost:8080"  # Ajuste conforme necessário


def test_health():
    """Testa o endpoint de health check"""
    print("\n✓ Testando /health")
    url = urljoin(BASE_URL, "/health")
    try:
        resp = requests.get(url, timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {json.dumps(resp.json(), indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False


def test_config():
    """Testa o endpoint de config"""
    print("\n✓ Testando /api/instagram/config")
    url = urljoin(BASE_URL, "/api/instagram/config")
    try:
        resp = requests.get(url, timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {json.dumps(resp.json(), indent=2)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False


def test_user_profile():
    """Testa o endpoint de perfil do usuário"""
    print("\n✓ Testando /api/instagram/user_profile")
    url = urljoin(BASE_URL, "/api/instagram/user_profile")
    try:
        resp = requests.get(url, timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, indent=2)}")

        if resp.status_code == 200:
            payload = data.get("payload", {})
            print(f"\n  Perfil:")
            print(f"    - Username: {payload.get('username')}")
            print(f"    - Followers: {payload.get('followersCount')}")
            print(f"    - Posts: {payload.get('postsCount')}")

        return resp.status_code == 200
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False


def test_posts():
    """Testa o endpoint de posts"""
    print("\n✓ Testando /api/instagram/posts")
    url = urljoin(BASE_URL, "/api/instagram/posts")
    try:
        resp = requests.get(url, timeout=15)
        print(f"  Status: {resp.status_code}")
        data = resp.json()

        if resp.status_code == 200:
            posts = data.get("payload", [])
            print(f"  Total de posts: {len(posts)}")

            if posts:
                post = posts[0]
                print(f"\n  Primeiro post:")
                print(f"    - Type: {post.get('type')}")
                print(f"    - Caption: {post.get('caption', '')[:50]}...")
                print(f"    - Media items: {len(post.get('media', []))}")
                print(f"    - Likes: {post.get('likesCount')}")
                print(f"    - Comments: {post.get('commentsCount')}")

                # Teste a primeira mídia
                if post.get('media'):
                    media = post['media'][0]
                    print(f"\n  Primeira mídia:")
                    print(f"    - Type: {media.get('type')}")
                    print(f"    - URL: {media.get('url')}")
                    print(f"    - ID: {media.get('id')}")
        else:
            print(f"  Response: {json.dumps(data, indent=2)}")

        return resp.status_code == 200
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False


def test_media_proxy(media_id: str):
    """Testa o endpoint de proxy de mídia"""
    print(f"\n✓ Testando /api/instagram/media_proxy?id={media_id}")
    url = urljoin(BASE_URL, f"/api/instagram/media_proxy?id={media_id}")
    try:
        resp = requests.get(url, timeout=15, stream=True)
        print(f"  Status: {resp.status_code}")
        print(f"  Content-Type: {resp.headers.get('Content-Type')}")
        print(f"  Content-Length: {resp.headers.get('Content-Length')}")
        print(f"  Accept-Ranges: {resp.headers.get('Accept-Ranges')}")

        if resp.status_code == 200:
            print(f"  ✓ Mídia carregada com sucesso!")

        return resp.status_code == 200
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False


def main():
    print("=" * 60)
    print("TESTE DE ENDPOINTS - INSTAGRAM API")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")

    results = {}

    # Testes básicos
    results['health'] = test_health()
    results['config'] = test_config()
    results['user_profile'] = test_user_profile()
    results['posts'] = test_posts()

    # Se posts funcionou, testa media_proxy
    if results['posts']:
        # Será testado no teste de posts
        pass

    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✓ PASSOU" if result else "✗ FALHOU"
        print(f"{test_name:20} {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} testes passaram")

    if passed == total:
        print("\n✓ Todos os testes passaram!")
    else:
        print(f"\n✗ {total - passed} teste(s) falharam")


if __name__ == "__main__":
    main()