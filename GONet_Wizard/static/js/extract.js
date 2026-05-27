// GONet_Wizard/static/js/extract.js
(() => {

  function updateShapeVisibility(root = document) {

    const shapeSelect = root.getElementById("extract-shape");
    if (!shapeSelect) return;

    const note = root.getElementById("extract-shape-note");

    const shapeGroups = root.querySelectorAll("[data-shape-group]");

    const shape = (shapeSelect.value || "").trim();

    shapeGroups.forEach((el) => {

      const allowed = (el.dataset.shapeGroup || "")
        .split(/\s+/)
        .filter(Boolean);

      const show =
        !shape || shape === "interactive"
          ? allowed.includes("interactive")
          : allowed.includes(shape);

      el.classList.toggle("hidden", !show);
    });

    if (!shape || shape === "interactive") {
      note?.classList.remove("hidden");
    } else {
      note?.classList.add("hidden");
    }
  }

  function combinePair(root, aId, bId, hiddenId) {

    const a = root.getElementById(aId);
    const b = root.getElementById(bId);
    const hidden = root.getElementById(hiddenId);

    if (!a || !b || !hidden) return;

    const av = (a.value || "").trim();
    const bv = (b.value || "").trim();

    if (!av && !bv) {
      hidden.value = "";
      return;
    }

    hidden.value = `${av},${bv}`;
  }

  function updateCombinedFields(root = document) {

    combinePair(
      root,
      "extract-center-x",
      "extract-center-y",
      "extract-center"
    );

    combinePair(
      root,
      "extract-width",
      "extract-height",
      "extract-sides"
    );

    combinePair(
      root,
      "extract-angle-start",
      "extract-angle-end",
      "extract-angles"
    );
  }

  function initCombinedFieldListeners(root = document) {

    const pairs = [
      ["extract-center-x", "extract-center-y"],
      ["extract-width", "extract-height"],
      ["extract-angle-start", "extract-angle-end"],
    ];

    pairs.forEach(([aId, bId]) => {

      const a = root.getElementById(aId);
      const b = root.getElementById(bId);

      [a, b].forEach((el) => {

        if (!el) return;

        el.addEventListener("input", () => {
          updateCombinedFields(root);
        });

        el.addEventListener("change", () => {
          updateCombinedFields(root);
        });
      });
    });

    updateCombinedFields(root);
  }

  function initExtractForm(root = document) {

    const shapeSelect = root.getElementById("extract-shape");

    if (!shapeSelect) return;

    shapeSelect.addEventListener("change", () => {
      updateShapeVisibility(root);
    });

    updateShapeVisibility(root);

    initCombinedFieldListeners(root);
  }

  // Export public API
  window.GONet = window.GONet || {};
  window.GONet.extract = {
    initExtractForm,
    updateShapeVisibility,
    updateCombinedFields,
  };

})();