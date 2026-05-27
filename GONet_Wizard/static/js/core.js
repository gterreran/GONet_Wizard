// GONet_Wizard/static/js/core.js
(() => {

  document.addEventListener("DOMContentLoaded", () => {

    // Browse buttons
    window.GONet?.browse?.initBrowseButtons?.(document);

    // Cached inputs
    window.GONet?.cache?.initCachedInputs?.(document);

    // Extract form dynamic behavior
    window.GONet?.extract?.initExtractForm?.(document);

  });

})();