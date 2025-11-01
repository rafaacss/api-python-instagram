// widget-loader.ts - Carrega o widget Vue similar ao elfsight
import { createApp } from 'vue';
import InstagramWidget from './components/InstagramWidget.vue';
// Importa CSS para que seja incluído no bundle
import './main.css';

interface WidgetConfig {
  apiUrl?: string;
  title?: string;
  instagramUrl?: string;
  showCaptions?: boolean;
  showPeek?: boolean;
}

class InstagramFeedLoader {
  private initialized = false;
  private widgets: HTMLElement[] = [];

  initialize() {
    if (this.initialized) return;
    this.initialized = true;

    // Aguarda o DOM estar pronto
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.collectAndInitWidgets());
    } else {
      this.collectAndInitWidgets();
    }

    // Observa mudanças no DOM para widgets adicionados dinamicamente
    this.observeDOM();
  }

  collectAndInitWidgets() {
    // Busca todas as divs com classe que começa com 'instagram-feed-widget'
    const elements = document.querySelectorAll<HTMLElement>('[class*="instagram-feed-widget"]');

    elements.forEach(element => {
      if (!this.widgets.includes(element)) {
        this.initWidget(element);
        this.widgets.push(element);
      }
    });
  }

  initWidget(element: HTMLElement) {
    // Extrai configuração dos atributos data-*
    const config: WidgetConfig = {
      apiUrl: element.dataset.apiUrl || element.getAttribute('data-api-url') || 'https://api-instagram.redbeauty.com.br/api/instagram/posts',
      title: element.dataset.title || element.getAttribute('data-title') || '',
      instagramUrl: element.dataset.instagramUrl || element.getAttribute('data-instagram-url') || '',
      showCaptions: this.parseBoolean(element.dataset.showCaptions || element.getAttribute('data-show-captions')),
      showPeek: this.parseBoolean(element.dataset.showPeek || element.getAttribute('data-show-peek')),
    };

    // Cria a aplicação Vue no elemento
    const app = createApp(InstagramWidget, config);
    app.mount(element);
  }

  parseBoolean(value: string | null | undefined): boolean {
    if (!value) return false;
    return value === 'true' || value === '1' || value === 'yes';
  }

  observeDOM() {
    if (typeof MutationObserver === 'undefined') return;

    const observer = new MutationObserver((mutations) => {
      let hasNewWidgets = false;

      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node instanceof HTMLElement) {
            // Verifica se o nó adicionado é um widget ou contém widgets
            const widgets = node.classList.contains('instagram-feed-widget')
              ? [node]
              : Array.from(node.querySelectorAll<HTMLElement>('[class*="instagram-feed-widget"]'));

            if (widgets.length > 0) {
              hasNewWidgets = true;
            }
          }
        });
      });

      if (hasNewWidgets) {
        this.collectAndInitWidgets();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }
}

// Exporta globalmente para uso como script
declare global {
  interface Window {
    InstagramFeedLoader: InstagramFeedLoader;
  }
}

// Cria instância global e inicializa automaticamente
const loader = new InstagramFeedLoader();
window.InstagramFeedLoader = loader;
loader.initialize();

export default loader;
