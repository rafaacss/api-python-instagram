#!/usr/bin/env python3
"""
Script de diagnóstico rápido - identifica exatamente qual é o problema
Uso: python quick_fix.py
"""

import os
import sys
import json
from pathlib import Path


class Diagnostic:
    def __init__(self):
        self.current_dir = Path.cwd()
        self.problems = []
        self.warnings = []
        self.success = []

    def check_static_files(self):
        """Verifica arquivos estáticos"""
        print("\n🔍 Verificando arquivos estáticos...")

        static_dir = self.current_dir / "static" / "instagram"

        if not static_dir.exists():
            self.problems.append(f"Diretório não existe: {static_dir}")
            print(f"  ✗ Diretório não existe: {static_dir}")
            return

        print(f"  ✓ Diretório existe: {static_dir}")

        required_files = ["mock_posts.json"]

        for filename in required_files:
            filepath = static_dir / filename
            if not filepath.exists():
                self.problems.append(f"Arquivo faltando: {filepath}")
                print(f"  ✗ {filename} - NÃO ENCONTRADO")
            else:
                # Tentar validar JSON
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        json.load(f)
                    self.success.append(f"Arquivo válido: {filename}")
                    print(f"  ✓ {filename} - OK (JSON válido)")
                except json.JSONDecodeError as e:
                    self.problems.append(f"JSON inválido em {filename}: {e}")
                    print(f"  ✗ {filename} - JSON INVÁLIDO: {e}")
                except Exception as e:
                    self.problems.append(f"Erro ao ler {filename}: {e}")
                    print(f"  ✗ {filename} - ERRO: {e}")

        # Listar outros arquivos
        print(f"\n  Outros arquivos em {static_dir}:")
        for file in static_dir.iterdir():
            if file.is_file():
                size = file.stat().st_size
                print(f"    - {file.name} ({size} bytes)")

    def check_directories(self):
        """Verifica diretórios importantes"""
        print("\n🔍 Verificando diretórios...")

        dirs = {
            "src/app": "Código da aplicação",
            "src/app/services": "Serviços",
            "src/app/routes": "Rotas",
            "static": "Arquivos estáticos",
            "static/instagram": "Arquivos estáticos do Instagram",
            "cache": "Cache",
            "cache/instagram": "Cache de mídia"
        }

        for rel_path, description in dirs.items():
            full_path = self.current_dir / rel_path
            if full_path.exists():
                self.success.append(f"Diretório existe: {rel_path}")
                print(f"  ✓ {rel_path:25} ({description})")
            else:
                self.warnings.append(f"Diretório não existe: {rel_path}")
                print(f"  ⚠ {rel_path:25} - Criando...")
                full_path.mkdir(parents=True, exist_ok=True)

    def check_python_files(self):
        """Verifica arquivos Python importantes"""
        print("\n🔍 Verificando arquivos Python...")

        files = {
            "src/app/__init__.py": "App initialization",
            "src/app/extensions.py": "Extensions (CORS)",
            "src/app/services/media_cache.py": "Media cache service",
            "src/app/routes/instagram.py": "Instagram routes",
            "src/app/routes/static_files.py": "Static files routes"
        }

        for rel_path, description in files.items():
            full_path = self.current_dir / rel_path
            if full_path.exists():
                self.success.append(f"Arquivo existe: {rel_path}")
                print(f"  ✓ {rel_path:40} ({description})")
            else:
                self.warnings.append(f"Arquivo faltando: {rel_path}")
                print(f"  ⚠ {rel_path:40} - FALTANDO")

    def check_env_file(self):
        """Verifica arquivo .env"""
        print("\n🔍 Verificando arquivo .env...")

        env_file = self.current_dir / ".env"
        if not env_file.exists():
            self.warnings.append(".env não encontrado")
            print("  ⚠ .env não encontrado")
            return

        print("  ✓ .env existe")

        required_vars = [
            "INSTAGRAM_ACCESS_TOKEN",
            "INSTAGRAM_BUSINESS_ACCOUNT_ID",
            "API_BASE_URL",
            "MEDIA_CACHE_DIR"
        ]

        try:
            with open(env_file, 'r') as f:
                content = f.read()
                for var in required_vars:
                    if var in content:
                        print(f"    ✓ {var} definido")
                    else:
                        self.warnings.append(f"{var} não definido em .env")
                        print(f"    ⚠ {var} não definido")
        except Exception as e:
            self.problems.append(f"Erro ao ler .env: {e}")
            print(f"  ✗ Erro ao ler .env: {e}")

    def check_permissions(self):
        """Verifica permissões"""
        print("\n🔍 Verificando permissões...")

        dirs_to_check = [
            "cache/instagram",
            "static/instagram"
        ]

        for dir_path in dirs_to_check:
            full_path = self.current_dir / dir_path
            if full_path.exists():
                if os.access(full_path, os.W_OK):
                    print(f"  ✓ {dir_path:30} - Escrita OK")
                else:
                    self.warnings.append(f"Sem permissão de escrita: {dir_path}")
                    print(f"  ⚠ {dir_path:30} - Sem escrita (execute: chmod 755 {dir_path})")

    def show_solution(self):
        """Mostra solução baseada nos problemas encontrados"""
        print("\n" + "=" * 60)
        print("DIAGNÓSTICO")
        print("=" * 60)

        if not self.problems and not self.warnings:
            print("✓ Tudo OK! Nenhum problema encontrado.")
            return

        if self.problems:
            print(f"\n🚨 PROBLEMAS CRÍTICOS ({len(self.problems)}):")
            for i, problem in enumerate(self.problems, 1):
                print(f"  {i}. {problem}")

        if self.warnings:
            print(f"\n⚠ AVISOS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")

        print("\n" + "=" * 60)
        print("SOLUÇÃO RÁPIDA")
        print("=" * 60)

        # Solução 1: Criar estrutura
        if any("Diretório não existe" in p for p in self.problems + self.warnings):
            print("\n1️⃣  CRIAR ESTRUTURA DE DIRETÓRIOS:")
            print("   python check_structure.py")

        # Solução 2: Criar arquivos JSON
        if any("mock_posts.json" in p for p in self.problems):
            print("\n2️⃣  CRIAR ARQUIVO mock_posts.json:")
            print(f"   Copie o arquivo 'mock_posts.json' fornecido para:")
            print(f"   {self.current_dir}/static/instagram/mock_posts.json")

        # Solução 3: Atualizar permissões
        if any("permissão" in w.lower() for w in self.warnings):
            print("\n3️⃣  CORRIGIR PERMISSÕES:")
            print("   chmod 755 cache/instagram")
            print("   chmod 755 static/instagram")

        # Solução 4: Atualizar arquivos Python
        if any("faltando" in w.lower() for w in self.warnings):
            print("\n4️⃣  ATUALIZAR ARQUIVOS PYTHON:")
            print("   - Copie o arquivo 'init_app.py' para 'src/app/__init__.py'")
            print("   - Copie o arquivo 'extensions.py' para 'src/app/extensions.py'")
            print("   - Copie o arquivo 'static_files.py' para 'src/app/routes/static_files.py'")
            print("   - Atualize 'src/app/services/media_cache.py'")
            print("   - Atualize 'src/app/routes/instagram.py'")

        # Solução 5: Testar
        print("\n5️⃣  TESTAR ENDPOINTS:")
        print("   python test_endpoints.py")

    def run(self):
        """Executa todo o diagnóstico"""
        print("\n" + "=" * 60)
        print("DIAGNÓSTICO RÁPIDO - INSTAGRAM API")
        print("=" * 60)
        print(f"Diretório: {self.current_dir}")

        self.check_directories()
        self.check_static_files()
        self.check_python_files()
        self.check_env_file()
        self.check_permissions()
        self.show_solution()

        print("\n" + "=" * 60)
        print(f"RESUMO: {len(self.success)} OK | {len(self.warnings)} avisos | {len(self.problems)} problemas")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    diagnostic = Diagnostic()
    diagnostic.run()