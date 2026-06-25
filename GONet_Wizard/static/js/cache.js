// GONet_Wizard/static/js/cache.js
(() => {
  function cacheKeyFor(el) {
    // Explicit key wins
    if (el.dataset.cacheKey) return el.dataset.cacheKey;

    // Otherwise build from form prefix + name
    const form = el.closest("form");
    const prefix = form?.dataset.cachePrefix;
    const name = el.name;

    if (!prefix || !name) return null;
    return `${prefix}::${name}`;
  }

  function restoreOne(el, key) {
    const raw = localStorage.getItem(key);
    if (raw === null) return;

    const type = (el.type || "").toLowerCase();

    if (type === "checkbox") {
      el.checked = (raw === "1");
      return;
    }
    if (type === "radio") {
      // For radios we store selected value on the group key
      if (el.value === raw) el.checked = true;
      return;
    }
    // text/select/textarea
    if ((el.value || "").trim() === "") el.value = raw;
  }

  function saveOne(el, key) {
    const type = (el.type || "").toLowerCase();

    if (type === "checkbox") {
      localStorage.setItem(key, el.checked ? "1" : "0");
      return;
    }
    if (type === "radio") {
      if (el.checked) localStorage.setItem(key, el.value);
      return;
    }

    const v = (el.value || "").trim();
    if (v) localStorage.setItem(key, v);
    else localStorage.removeItem(key);
  }

  function saveCachedInputs(root) {
    const els = root.querySelectorAll("[data-cache='1']");
    els.forEach((el) => {
      const key = cacheKeyFor(el);
      if (!key) return;
      saveOne(el, key);
    });
  }

  function initCachedInputs(root = document) {
    const els = root.querySelectorAll("[data-cache='1']");
    els.forEach((el) => {
      const key = cacheKeyFor(el);
      if (!key) return;

      // Restore
      restoreOne(el, key);

      // Save on user change
      const handler = () => saveOne(el, key);

      el.addEventListener("change", handler);

      // for text inputs, save while typing
      if (
        el.tagName === "INPUT" &&
        !["checkbox", "radio"].includes((el.type || "").toLowerCase())
      ) {
        el.addEventListener("input", handler);
      }
    });
  }

  // Export public API (only)
  window.GONet = window.GONet || {};
  window.GONet.cache = { saveCachedInputs, initCachedInputs };
})();
