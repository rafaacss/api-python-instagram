<template>
	<div :class="elfsightClass" class="eapps-instagram-feed es-widget eapps-widget" data-elfsight-app-lazy></div>
</template>

<script setup>
import { onMounted, ref } from 'vue';

const sectionClass = 'js-swiper-instafeed';
const elfsightClass = 'elfsight-app-redbeauty';

onMounted(() => {
	// Carrega Elfsight
	const script = document.createElement('script');
	script.src = 'https://api-instagram.redbeauty.com.br/static/instagram/instagram.js?v=' + Date.now();
	script.async = true;
	document.head.appendChild(script);

	// Remove branding após algum tempo
	let tentativas = 0;
	const removerBranding = () => {
		document.querySelectorAll('a[href*="elfsight.com/instagram-feed-instashow"]').forEach(el => el.remove());
	};
	const intervalo = setInterval(() => {
		removerBranding();
		tentativas++;
		if (tentativas > 30) clearInterval(intervalo);
	}, 500);
});
</script>
