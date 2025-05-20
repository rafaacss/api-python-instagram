const scriptsToLoad = [
    "https://api-instagram.redbeauty.com.br/static/instagram/instagram.js",
    "https://api-instagram.redbeauty.com.br/static/instagram/instashow.js"
];

scriptsToLoad.forEach(src => {
    const script = document.createElement('script');
    script.src = src + '?v=' + Date.now(); // Cache busting para sempre pegar a versão nova
    script.async = false; // Mantenha a ordem de carregamento, se necessário
    document.head.appendChild(script);
});