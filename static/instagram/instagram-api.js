(function () {
  const configUrl = "/api/instagram/config";
  const subscribers = [];
  let base = null; // null = ainda carregando; string = resolvido; "" = falhou

  function notify() {
    while (subscribers.length) {
      try { subscribers.shift()(base || ""); } catch (_) {}
    }
  }

  // expõe no global
  window.InstagramAPI = {
    ready(cb) {
      if (typeof cb !== "function") return;
      if (base !== null) cb(base || "");
      else subscribers.push(cb);
    },
    url(endpoint) {
      const e = String(endpoint || "").replace(/^\//, "");
      const b = String(base || "").replace(/\/+$/, "");
      return b ? `${b}/${e}` : `/${e}`;
    }
  };

  // busca a config
  fetch(configUrl, { credentials: "omit" })
    .then(r => r.json())
    .then(j => {
      base = (j && j.payload && j.payload.apiBaseUrl) || "";
      notify();
    })
    .catch(() => { base = ""; notify(); });
})();
