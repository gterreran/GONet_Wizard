// GONet_Wizard/static/js/browse.js
(() => {
  async function browseAndFill(btn) {
    const targetId = btn.dataset.targetId;
    const mode = btn.dataset.pickMode || "files_or_folder";
    const input = document.getElementById(targetId);
    if (!input) return;

    // Must run inside pywebview
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.pick_paths) {
      alert("Browse is available only in the desktop app (pywebview).");
      return;
    }

    try {
      const paths = await window.pywebview.api.pick_paths(mode);
      if (!paths || paths.length === 0) return;

      // If there is already text, append with ", "
      const existing = (input.value || "").trim();
      const addition = paths.join(", ");
      input.value = existing ? `${existing}, ${addition}` : addition;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (err) {
      console.error(err);
      alert("Failed to open file picker.");
    }
  }

  function initBrowseButtons(root = document) {
    root.querySelectorAll(".browse-button").forEach((btn) => {
      btn.addEventListener("click", () => browseAndFill(btn));
    });
  }

  // Export public API (only)
  window.GONet = window.GONet || {};
  window.GONet.browse = { initBrowseButtons };
})();
