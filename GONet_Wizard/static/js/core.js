// GONet_Wizard/static/js/core.js
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    // Initialize browse buttons + cached inputs globally
    window.GONet?.browse?.initBrowseButtons?.(document);
    window.GONet?.cache?.initCachedInputs?.(document);
  });
})();
