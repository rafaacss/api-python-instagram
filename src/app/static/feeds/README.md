# Instagram Feed Widget

Widget Vue.js para exibir feed do Instagram, similar ao componente Elfsight.

## 🚀 Como Usar

### Uso Básico (Similar ao Elfsight)

```html
<!-- 1. Inclua o script do widget -->
<script type="module" src="/static/feeds/instagram-feed-widget.js"></script>

<!-- 2. Adicione a div do widget onde quiser exibir o feed -->
<div class="instagram-feed-widget"
     data-api-url="https://api-instagram.redbeauty.com.br/api/instagram/posts"
     data-title="@redbeauty"
     data-instagram-url="https://instagram.com/redbeauty"
     data-show-captions="true"
     data-show-peek="true">
</div>
```

### Atributos Disponíveis

| Atributo | Descrição | Padrão | Obrigatório |
|----------|-----------|--------|-------------|
| `data-api-url` | URL da API de posts do Instagram | - | ✅ Sim |
| `data-title` | Título exibido acima do feed | - | ❌ Não |
| `data-instagram-url` | URL do perfil do Instagram | - | ❌ Não |
| `data-show-captions` | Exibir legendas dos posts (`true`/`false`) | `false` | ❌ Não |
| `data-show-peek` | Mostrar preview do próximo item (`true`/`false`) | `false` | ❌ Não |

## 📦 Estrutura de Arquivos

```
feeds/
├── src/                          # Código fonte
│   ├── components/
│   │   └── InstagramWidget.vue  # Componente principal
│   ├── App.vue                  # App SPA (para testes)
│   ├── main.ts                  # Entry point SPA
│   └── widget-loader.ts         # Loader do widget (similar ao elfsight)
├── dist/                        # Build (gerado)
│   ├── instagram-feed-widget.js # Script principal do widget
│   ├── index.html              # SPA (para testes)
│   └── assets/                 # CSS e JS chunks
├── widget-example.html         # Exemplo de uso
├── package.json
├── vite.config.js
└── README.md
```

## 🔧 Desenvolvimento

### Instalar dependências

```bash
npm install
```

### Modo desenvolvimento

```bash
npm run dev
```

### Build para produção

```bash
npm run build
```

## 🌐 Rotas Disponíveis

- `/feeds` - SPA de teste do widget
- `/feeds/example` - Página de exemplo de uso (similar ao elfsight)
- `/static/feeds/instagram-feed-widget.js` - Script do widget
- `/static/feeds/assets/*` - Assets (CSS, JS chunks)

## 📋 Exemplo Completo

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meu Site</title>
</head>
<body>
    <h1>Feed do Instagram</h1>

    <!-- Widget 1 - Com todas as opções -->
    <div class="instagram-feed-widget"
         data-api-url="https://api-instagram.redbeauty.com.br/api/instagram/posts"
         data-title="@redbeauty"
         data-instagram-url="https://instagram.com/redbeauty"
         data-show-captions="true"
         data-show-peek="true">
    </div>

    <!-- Widget 2 - Minimalista -->
    <div class="instagram-feed-widget"
         data-api-url="https://api-instagram.redbeauty.com.br/api/instagram/posts">
    </div>

    <!-- Carrega o widget loader -->
    <script type="module" src="/static/feeds/instagram-feed-widget.js"></script>
</body>
</html>
```

## 🎨 Funcionalidades

- ✅ Carrossel de posts do Instagram
- ✅ Modal para visualização de posts
- ✅ Suporte a imagens, vídeos e carrosséis
- ✅ Navegação por teclado
- ✅ Responsivo
- ✅ Lazy loading de imagens
- ✅ Exibição de legendas, likes e comentários
- ✅ Link para visualização no Instagram
- ✅ Comportamento similar ao componente Elfsight

## 🔄 Diferenças do Elfsight

### Elfsight
```html
<div class="elfsight-app-redbeauty eapps-instagram-feed es-widget eapps-widget"></div>
<script src="instagram.js"></script>
```

### Nosso Widget
```html
<div class="instagram-feed-widget" data-api-url="..."></div>
<script type="module" src="/static/feeds/instagram-feed-widget.js"></script>
```

**Vantagens do nosso widget:**
- ✅ Código fonte acessível e customizável
- ✅ Sem dependência de serviços externos
- ✅ API própria
- ✅ Build otimizado com Vite
- ✅ TypeScript
- ✅ Vue 3 Composition API

## 📝 Notas

- O widget usa ES modules (`type="module"`), portanto funciona apenas em navegadores modernos
- Os assets (CSS/JS) são carregados automaticamente pelo widget loader
- O widget detecta automaticamente novos elementos adicionados ao DOM
- Suporta múltiplos widgets na mesma página
