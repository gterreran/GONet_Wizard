// GONet_Wizard/static/js/launcher.js

function saveCachedInputs(root) {
  const els = root.querySelectorAll("[data-cache='1']");
  els.forEach((el) => {
    const key = _cacheKeyFor(el);
    if (!key) return;
    _saveOne(el, key);
  });
}

function submitForm(event) {
  event.preventDefault();
  const form = event.target;

  const formData = new FormData(form);

  // Build payload while preserving repeated keys as arrays
  const payload = {};
  for (const [k, v] of formData.entries()) {
    if (payload[k] === undefined) payload[k] = v;
    else if (Array.isArray(payload[k])) payload[k].push(v);
    else payload[k] = [payload[k], v];
  }

  // OPTIONAL debug: verify hidden flags are included
  console.log("Submitting payload:", payload);

  fetch('/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(data => {
      // Prefer actual command output if provided; fallback to message
      const out = (data.output !== undefined) ? data.output : data.message;

      const outEl = document.getElementById('output');
      outEl.innerHTML = out;

      // ✅ Only persist if the command actually ran successfully
      if (data.status === "success") {
        saveCachedInputs(form);
      }
    });
}
  
// Optional: modal control (for exit confirmation)
function showExitModal() {
  document.getElementById('exit-modal').classList.remove('hidden');
}
  
function closeExitModal() {
  document.getElementById('exit-modal').classList.add('hidden');
}

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

function _cacheKeyFor(el) {
  // Explicit key wins
  if (el.dataset.cacheKey) return el.dataset.cacheKey;

  // Otherwise build from form prefix + name
  const form = el.closest("form");
  const prefix = form?.dataset.cachePrefix;
  const name = el.name;

  if (!prefix || !name) return null;
  return `${prefix}::${name}`;
}

function _restoreOne(el, key) {
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

function _saveOne(el, key) {
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

function initCachedInputs(root = document) {
  const els = root.querySelectorAll("[data-cache='1']");
  els.forEach((el) => {
    const key = _cacheKeyFor(el);
    if (!key) return;

    // Restore
    _restoreOne(el, key);

    // Save on user change
    const handler = () => _saveOne(el, key);

    el.addEventListener("change", handler);
    // for text inputs, save while typing
    if (el.tagName === "INPUT" && !["checkbox", "radio"].includes((el.type || "").toLowerCase())) {
      el.addEventListener("input", handler);
    }
  });
}

function initBrowseButtons() {
  document.querySelectorAll(".browse-button").forEach((btn) => {
    btn.addEventListener("click", () => browseAndFill(btn));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initBrowseButtons();
  initCachedInputs();
});