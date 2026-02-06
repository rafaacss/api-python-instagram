# k6 PHP Benchmark - Gran Cursos Online

Ferramenta para comparar performance entre ambientes PHP 7.4 e PHP 8.5 usando k6 como engine de load testing.

## Arquitetura

```
frontend (Vue.js/Nginx :8080)  -->  api (Python/Flask :5000)  -->  k6 (load testing)
                                                                       |
                                                               URLs externas:
                                                         dev.grancursosonline.com.br
                                                         php8-5.grancursosonline.com.br
```

## Como usar

### 1. Subir os containers

```bash
cd k6-php-benchmark
docker compose up -d --build
```

### 2. Acessar a interface

Abra `http://localhost:8080` no navegador.

### 3. Configurar o teste

- **URL PHP 7.4**: ex: `https://dev.grancursosonline.com.br`
- **URL PHP 8.5**: ex: `https://php8-5.grancursosonline.com.br`
- **Tipo de teste**:
  - `Homepage` - testa carregamento da pagina inicial
  - `Endpoints` - testa endpoints especificos
  - `Autenticado` - faz login e testa endpoints autenticados
  - `Completo` - homepage + endpoints
- **VUs** - usuarios virtuais simultaneos
- **Duracao** - tempo do teste
- **Endpoints** - lista separada por virgula (ex: `/api/cursos,/dashboard`)
- **Login** - credenciais para testes autenticados

### 4. Executar

Clique em "Executar Benchmark Comparativo" e aguarde os resultados.

## API REST

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/compare` | Executa benchmark comparativo |
| POST | `/api/test` | Executa teste unico |
| GET | `/api/results` | Lista resultados salvos |
| GET | `/api/results/:file` | Retorna resultado especifico |

### Exemplo via curl

```bash
curl -X POST http://localhost:5000/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "url_php74": "https://dev.grancursosonline.com.br",
    "url_php85": "https://php8-5.grancursosonline.com.br",
    "test_type": "homepage",
    "vus": 10,
    "duration": "30s"
  }'
```

## Estrutura

```
k6-php-benchmark/
  api/
    app.py              # Backend Flask + SocketIO
    requirements.txt
    Dockerfile
  frontend/
    index.html          # Vue.js SPA
    Dockerfile
  k6/
    benchmark.js        # Script k6 com suporte a login
  results/              # Resultados salvos (JSON)
  docker-compose.yml
```
