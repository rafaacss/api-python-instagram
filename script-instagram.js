<script>
// Carrega o Elfsight Instagram Feed
var elfsightScript = document.createElement('script');
elfsightScript.src = 'https://static.elfsight.com/platform/platform.js';
elfsightScript.async = true;
document.head.appendChild(elfsightScript);

function removerBrandingElfsight() {
    var els = document.querySelectorAll('a[href*="elfsight.com/instagram-feed-instashow"]');
    for (var i = 0; i < els.length; i++) {
        els[i].parentNode.removeChild(els[i]);
    }
}

function substituirInstafeedPorElfsight() {
    var section = document.querySelector('section .js-swiper-instafeed');
    if (section) {
        section.innerHTML = '';
        var elfsightDiv = document.createElement('div');
        elfsightDiv.className = 'elfsight-app-7d812c10-bcfd-4950-a029-d71810d13b59';
        elfsightDiv.setAttribute('data-elfsight-app-lazy', '');
        section.appendChild(elfsightDiv);
    }
}

// Aguarda o carregamento do DOM
window.addEventListener('DOMContentLoaded', function() {
    substituirInstafeedPorElfsight();

    // Roda a cada 500ms por até 15s para garantir que o branding seja removido, mesmo se o widget demorar
    var tentativas = 0;
    var intervalo = setInterval(function() {
        removerBrandingElfsight();
        tentativas++;
        if (tentativas > 30) clearInterval(intervalo); // Para após 15 segundos
    }, 500);
});


</script>
