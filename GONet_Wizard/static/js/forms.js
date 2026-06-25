// GONet_Wizard/static/js/forms.js
(() => {
  function payloadFromForm(form) {
    const formData = new FormData(form);

    // Build payload while preserving repeated keys as arrays
    const payload = {};
    for (const [k, v] of formData.entries()) {
      if (payload[k] === undefined) payload[k] = v;
      else if (Array.isArray(payload[k])) payload[k].push(v);
      else payload[k] = [payload[k], v];
    }
    return payload;
  }

  function renderOutput(data) {
    // Prefer actual command output if provided; fallback to message
    const out = (data.output !== undefined) ? data.output : data.message;
    const outEl = document.getElementById("output");
    if (outEl) outEl.innerHTML = out;
  }

  function submitForm(event) {
    event.preventDefault();
    const form = event.target;

    window.GONet?.extract?.updateCombinedFields?.(document);
    const payload = payloadFromForm(form);

    // OPTIONAL debug: verify hidden flags are included
    console.log("Submitting payload:", payload);

    fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((r) => r.json())
      .then((data) => {
        renderOutput(data);

        // ✅ Only persist if the command actually ran successfully
        if (data.status === "success") {
          if (window.GONet?.cache?.saveCachedInputs) {
            window.GONet.cache.saveCachedInputs(form);
          }
        }
      });
  }

  // Export public API (only)
  window.GONet = window.GONet || {};
  window.GONet.forms = { submitForm };
})();
