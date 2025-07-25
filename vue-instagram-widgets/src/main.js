import { createApp } from 'vue';
import ElfsightFeed from './components/ElfsightFeed.vue';
import Servicos from './components/Servicos.vue';

async function injectCSS(url) {
    const res = await fetch(url);
    const css = await res.text();
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
}

// Chamada para injetar o CSS externo no head
injectCSS('/static/main.css');

// Função reutilizável que verifica se o elemento existe e monta o componente
function mountIfExists(component, mountId) {
    const el = document.getElementById(mountId);
    if (el) {
        createApp(component).mount(el);
    }
}

mountIfExists(ElfsightFeed, 'vue-instafeed-app'); // Página inicial
mountIfExists(Servicos, 'vue-servicos-app');      // Página de serviços
