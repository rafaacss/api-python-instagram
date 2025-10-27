#!/usr/bin/env python3
"""
Script para verificar a estrutura de diretórios e arquivos da aplicação
Uso: python check_structure.py
"""

import os
import json


def check_directory_structure():
    """Verifica a estrutura de diretórios do projeto"""
    print("\n" + "=" * 60)
    print("VERIFICAÇÃO DE ESTRUTURA DE DIRETÓRIOS")
    print("=" * 60)

    # Verificar diretório atual
    current_dir = os.getcwd()
    print(f"\nDiretório atual: {current_dir}")

    # Estrutura esperada
    expected_dirs = [
        "src",
        "src/app",
        "src/app/services",
        "src/app/routes",
        "static",
        "static/instagram",
        "cache",
        "cache/instagram",
        "logs"
    ]

    print("\n✓ Diretórios esperados:")
    for dir_path in expected_dirs:
        full_path = os.path.join(current_dir, dir_path)
        exists = os.path.isdir(full_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_path}")

        if not exists:
            print(f"     CRIANDO: {full_path}")
            os.makedirs(full_path, exist_ok=True)

    # Verificar arquivos principais
    print("\n✓ Arquivos principais em src/app:")
    expected_app_files = [
        "__init__.py",
        "config.py",
        "extensions.py"
    ]

    for file_name in expected_app_files:
        file_path = os.path.join(current_dir, f"src/app/{file_name}")
        exists = os.path.isfile(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_name}")

    # Verificar services
    print("\n✓ Services em src/app/services:")
    expected_services = [
        "__init__.py",
        "cache.py",
        "http.py",
        "instagram.py",
        "media_cache.py",
        "warmup.py"
    ]

    for file_name in expected_services:
        file_path = os.path.join(current_dir, f"src/app/services/{file_name}")
        exists = os.path.isfile(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_name}")

    # Verificar routes
    print("\n✓ Routes em src/app/routes:")
    expected_routes = [
        "__init__.py",
        "admin.py",
        "google.py",
        "health.py",
        "instagram.py",
        "static_files.py"
    ]

    for file_name in expected_routes:
        file_path = os.path.join(current_dir, f"src/app/routes/{file_name}")
        exists = os.path.isfile(file_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {file_name}")

    # Verificar arquivos estáticos
    print("\n✓ Arquivos em static/instagram:")
    static_dir = os.path.join(current_dir, "static/instagram")
    if os.path.isdir(static_dir):
        files = os.listdir(static_dir)
        if files:
            for file_name in files:
                file_path = os.path.join(static_dir, file_name)
                file_size = os.path.getsize(file_path)
                print(f"  ✓ {file_name} ({file_size} bytes)")
        else:
            print("  ✗ Nenhum arquivo encontrado!")
    else:
        print(f"  ✗ Diretório não existe: {static_dir}")

    # Verificar cache
    print("\n✓ Diretório de cache:")
    cache_dir = os.path.join(current_dir, "cache/instagram")
    if os.path.isdir(cache_dir):
        files = os.listdir(cache_dir)
        print(f"  {len(files)} arquivo(s) em cache")
        if len(files) <= 10:
            for file_name in files:
                print(f"    - {file_name}")
    else:
        print(f"  Criando: {cache_dir}")
        os.makedirs(cache_dir, exist_ok=True)


def check_json_files():
    """Verifica os arquivos JSON"""
    print("\n" + "=" * 60)
    print("VERIFICAÇÃO DE ARQUIVOS JSON")
    print("=" * 60)

    current_dir = os.getcwd()
    static_dir = os.path.join(current_dir, "static/instagram")

    json_files = [
        "mock_posts.json",
        "core-service-p-boot.json"
    ]

    for json_file in json_files:
        file_path = os.path.join(static_dir, json_file)
        print(f"\n✓ {json_file}:")

        if not os.path.exists(file_path):
            print(f"  ✗ Arquivo não encontrado: {file_path}")
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"  ✓ JSON válido")
                print(f"  - Tamanho: {os.path.getsize(file_path)} bytes")

                # Mostrar estrutura
                if isinstance(data, dict):
                    print(f"  - Chaves: {', '.join(data.keys())}")

                    if 'payload' in data:
                        payload = data['payload']
                        if isinstance(payload, list):
                            print(f"  - Items em payload: {len(payload)}")
                elif isinstance(data, list):
                    print(f"  - Items: {len(data)}")
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON inválido: {e}")
        except Exception as e:
            print(f"  ✗ Erro ao ler: {e}")


def check_endpoints():
    """Mostra os endpoints disponíveis"""
    print("\n" + "=" * 60)
    print("ENDPOINTS DISPONÍVEIS")
    print("=" * 60)

    endpoints = {
        "Saúde": "/health",
        "Config": "/api/instagram/config",
        "Perfil do Usuário": "/api/instagram/user_profile",
        "Posts": "/api/instagram/posts",
        "Media Proxy": "/api/instagram/media_proxy?id=MEDIA_ID",
        "Warmup": "/api/instagram/warmup (POST)",
        "Limpar Cache": "/api/instagram/admin/clear_cache (POST)",
        "Avaliações Google": "/api/google/reviews",
        "Mock Posts": "/api/mock/posts",
        "Arquivo Estático": "/static/instagram/mock_posts.json"
    }

    for name, endpoint in endpoints.items():
        print(f"  - {name:20} {endpoint}")


def main():
    print("\n" + "=" * 60)
    print("VERIFICADOR DE ESTRUTURA DA APLICAÇÃO")
    print("=" * 60)

    check_directory_structure()
    check_json_files()
    check_endpoints()

    print("\n" + "=" * 60)
    print("DICAS")
    print("=" * 60)
    print("""
    1. Se faltarem diretórios, eles foram criados automaticamente
    2. Se faltarem arquivos JSON, crie-os em static/instagram/
    3. Exemplo de mock_posts.json:
    {
        "code": 200,
        "payload": [...]
    }

    4. Testes recomendados:
       - curl http://localhost:8080/health
       - curl http://localhost:8080/api/instagram/config
       - curl http://localhost:8080/static/instagram/mock_posts.json
    """)


if __name__ == "__main__":
    main()