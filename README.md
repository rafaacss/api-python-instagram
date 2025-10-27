# INSTRUÇÕES DE IMPLEMENTAÇÃO DOS ARQUIVOS CORRIGIDOS

## Arquivos para atualizar no seu projeto

### 1. **src/app/extensions.py**
Replace o conteúdo completamente com o arquivo `extensions.py` fornecido.

```
Localização: src/app/extensions.py
Mudança: CORS agora expõe headers de range e accept-ranges para melhor suporte a vídeos
```

### 2. **src/app/__init__.py**
Replace o conteúdo completamente com o arquivo `init_app.py` fornecido.

```
Localização: src/app/__init__.py
Mudança: Adicionado logging detalhado e melhor tratamento de inicialização
```

### 3. **src/app/services/media_cache.py**
Replace o conteúdo completamente com o arquivo `media_cache.py` fornecido.

```
Localização: src/app/services/media_cache.py
Mudanças principais:
- Aumentado buffer de detecção de tipo de 16 para 32 bytes
- Adicionado logging extensivo em todas as operações
- Melhorada detecção de Content-Type com mapa explícito
- Melhorado tratamento de erros com mensagens descritivas
- Adicionado support para mais tipos de vídeo (MOV, AVI)
```

### 4. **src/app/services/warmup.py**
Replace o conteúdo completamente com o arquivo `warmup.py` fornecido.

```
Localização: src/app/services/warmup.py
Mudanças principais:
- Adicionado logging detalhado
- Melhor tratamento de erros
- Debug de cada etapa do processo
```

### 5. **src/app/routes/instagram.py**
Replace o conteúdo completamente com o arquivo `instagram.py` fornecido.

```
Localização: src/app/routes/instagram.py
Mudanças principais:
- Adicionado logging extensivo
- Melhorada validação de URLs (prefer_thumb agora funciona corretamente)
- Melhor tratamento de erros
- Melhor documentação de cada endpoint
```

---

## Arquivos OPCIONAIS (para melhor logging)

### 6. **logging_config.py** (OPCIONAL)
Crie um novo arquivo em `src/app/logging_config.py` com o conteúdo fornecido.

```
Localização: src/app/logging_config.py
Propósito: Configuração centralizada de logging com rotação de arquivos
```

Se usar, adicione ao seu `src/app/__init__.py`:
```python
from .logging_config import setup_logging

def create_app():
    # ... código existente ...
    app = Flask(__name__, static_folder='static')
    app.config.from_object(Settings)
    
    # Novo: configurar logging
    setup_logging(app)
    
    # ... resto do código ...
```

---

## Script de teste

### 7. **test_endpoints.py**
Coloque o arquivo `test_endpoints.py` na raiz do seu projeto.

```
Localização: ./test_endpoints.py
Uso: python test_endpoints.py
```

---

## Checklist de Implementação

- [ ] Atualize `src/app/extensions.py`
- [ ] Atualize `src/app/__init__.py` (renomeie de `init_app.py`)
- [ ] Atualize `src/app/services/media_cache.py`
- [ ] Atualize `src/app/services/warmup.py`
- [ ] Atualize `src/app/routes/instagram.py`
- [ ] (OPCIONAL) Crie `src/app/logging_config.py` e configure no `__init__.py`
- [ ] (OPCIONAL) Coloque `test_endpoints.py` na raiz do projeto
- [ ] Reinicie sua aplicação Flask
- [ ] Execute `python test_endpoints.py` para testar

---

## Mudanças Principais Implementadas

### 1. **Melhor Detecção de Tipo de Arquivo**
- Buffer aumentado de 16 para 32 bytes para detectar corretamente MP4
- Mapa explícito de extensões para Content-Type

### 2. **CORS Melhorado**
- Headers `Content-Range` e `Accept-Ranges` agora expostos
- Suporte melhor para HTTP Range requests (essential para vídeos)

### 3. **Logging Extensivo**
- Todas as operações críticas registradas em log
- Fácil debug se algo falhar
- Arquivo de log rotativo (se usar logging_config.py)

### 4. **Melhor Validação de URLs**
- A lógica de fallback para `media_url`/`thumbnail_url` agora funciona corretamente
- Menos erros silenciosos

### 5. **Tratamento de Erros**
- Mensagens de erro mais descritivas
- Menos casos onde erros são ignorados silenciosamente

---

## Observações Importantes

1. **Backup**: Antes de atualizar, faça backup dos arquivos originais
2. **Testes**: Execute o script `test_endpoints.py` após as mudanças
3. **Logs**: Verifique os logs se algo não funcionar
4. **Variáveis de Ambiente**: Certifique-se que `.env` está com valores corretos
5. **Permissões**: A pasta `cache/instagram` deve ter permissões de leitura/escrita

---

## Problemas Comuns

### "No media_url available"
- Verifique se o token do Instagram está correto
- Verifique se o USER_ID está correto
- Execute `/api/instagram/user_profile` para confirmar acesso

### Vídeos não carregam completamente
- Verifique `MEDIA_CACHE_MAX_BYTES` em `.env` (aumente se necessário)
- Verifique espaço em disco para cache

### Erro de permissão na pasta de cache
- Verifique permissões: `chmod 755 cache/instagram`
- Verifique espaço em disco

### Logs não aparecem
- Verifique o nível de log em `logging_config.py`
- Se não usar `logging_config.py`, os logs irão para console

---

## Próximos Passos

1. Implemente todos os arquivos acima
2. Reinicie a aplicação
3. Execute `python test_endpoints.py`
4. Verifique os logs para qualquer erro
5. Teste no navegador/frontend

Se ainda houver problemas, compartilhe:
- Saída de `test_endpoints.py`
- Logs da aplicação
- Mensagens de erro específicas