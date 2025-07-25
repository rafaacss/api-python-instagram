import { createApp } from 'vue';
import '../../static/main.css';

// Importação dos componentes Vue
import ElfsightFeed from './components/ElfsightFeed.vue';
import Servicos from './components/Servicos.vue';

// Função reutilizável que verifica se o elemento existe e monta o componente
function mountIfExists(component, mountId) {
    const el = document.getElementById(mountId);
    if (el) {
        createApp(component).mount(el);
    }
}

mountIfExists(ElfsightFeed, 'vue-instafeed-app'); // Página inicial
mountIfExists(Servicos, 'vue-servicos-app');      // Página de serviços
