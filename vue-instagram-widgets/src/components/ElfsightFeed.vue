<template>
<div style="display: none;"></div>
</template>

<script setup>
import { onMounted, ref } from 'vue';

const sectionClass = 'js-swiper-instafeed';
const elfsightClass = 'elfsight-app-redbeauty';

onMounted(() => {
	// 1. Localiza o container antigo
	const oldSection = document.querySelector('.js-ig-success.js-swiper-instafeed');

	if (oldSection) {
		// 2. Cria o novo widget Elfsight
		const elfsightDiv = document.createElement('div');
		elfsightDiv.className = `${elfsightClass} eapps-instagram-feed es-widget eapps-widget`;
		elfsightDiv.setAttribute('data-elfsight-app-lazy', '');

		// 3. Substitui o elemento antigo pelo novo
		oldSection.parentNode.replaceChild(elfsightDiv, oldSection);

		// 4. Carrega o script do Instagram/Elfsight
		const script = document.createElement('script');
		script.src = 'https://api-instagram.redbeauty.com.br/static/instagram/instagram.js?v=' + Date.now();
		script.async = true;
		document.head.appendChild(script);
	} else {
		// Opcional: log se não encontrar o container esperado
		console.warn('Não foi encontrado o container .js-ig-success.js-swiper-instafeed para substituir.');
	}
});
</script>
