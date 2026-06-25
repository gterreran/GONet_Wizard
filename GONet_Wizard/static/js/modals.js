// GONet_Wizard/static/js/modals.js
(() => {
  function showExitModal() {
    document.getElementById("exit-modal")?.classList.remove("hidden");
  }

  function closeExitModal() {
    document.getElementById("exit-modal")?.classList.add("hidden");
  }

  // Export public API (only)
  window.GONet = window.GONet || {};
  window.GONet.modals = { showExitModal, closeExitModal };
})();
