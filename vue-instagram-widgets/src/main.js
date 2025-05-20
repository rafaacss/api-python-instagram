import { createApp } from 'vue';
import ElfsightFeed from './components/ElfsightFeed.vue';

const mountPoint = document.createElement('div');
mountPoint.id = 'vue-instafeed-app';
document.body.appendChild(mountPoint);

createApp(ElfsightFeed).mount('#vue-instafeed-app');
