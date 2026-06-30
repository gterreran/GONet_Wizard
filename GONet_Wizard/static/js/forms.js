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
    if (outEl) outEl.innerHTML = out || "";
  }

  function terminalElements() {
    return {
      panel: document.getElementById("command-terminal"),
      status: document.getElementById("terminal-status"),
      output: document.getElementById("terminal-output"),
    };
  }

  function hasTerminalPanel() {
    const { panel, output } = terminalElements();
    return Boolean(panel && output);
  }

  function setTerminalStatus(statusEl, status) {
    if (!statusEl) return;

    const normalized = (status || "ready").toLowerCase();
    statusEl.textContent = normalized.charAt(0).toUpperCase() + normalized.slice(1);
    statusEl.classList.remove("is-ready", "is-running", "is-success", "is-error");
    statusEl.classList.add(`is-${normalized}`);
  }

  function commandLabelFromPayload(payload) {
    const command = payload.command || "command";
    return `GONet_Wizard ${command}`;
  }

  function stripAnsiControlSequences(text) {
    // Progress helpers sometimes emit ANSI cursor/clear-line sequences along
    // with carriage returns. A browser <pre> is not a real terminal, so strip
    // the escape codes before applying lightweight terminal-style updates.
    return String(text).replace(/[\u001B\u009B][[\]()#;?]*(?:(?:(?:[a-zA-Z\d]*(?:;[a-zA-Z\d]*)*)?\u0007)|(?:(?:\d{1,4}(?:;\d{0,4})*)?[\dA-PR-TZcf-nq-uy=><~]))/g, "");
  }

  function applyTerminalControlText(existingText, incomingText) {
    const text = stripAnsiControlSequences(incomingText);
    const lines = String(existingText || "").split("\n");
    let currentLine = lines.pop() || "";

    for (const char of text) {
      if (char === "\r") {
        // Same-line progress output uses carriage returns to repaint the
        // current line. Treat that as replacing the visible terminal line
        // instead of showing raw control characters or many duplicate lines.
        currentLine = "";
      } else if (char === "\n") {
        lines.push(currentLine);
        currentLine = "";
      } else if (char === "\b") {
        currentLine = currentLine.slice(0, -1);
      } else {
        currentLine += char;
      }
    }

    lines.push(currentLine);
    return lines.join("\n");
  }

  function startTerminal(payload) {
    const { panel, status, output } = terminalElements();
    if (!panel || !output) return;

    setTerminalStatus(status, "running");
    output.textContent = `$ ${commandLabelFromPayload(payload)}\nRUNNING: Command submitted. Opening feedback stream...`;
    output.scrollTop = output.scrollHeight;
  }

  function writeTerminalChunk(data) {
    const { panel, status, output } = terminalElements();
    if (!panel || !output || !data) return;

    if (data.status) {
      setTerminalStatus(status, data.status);
    }

    if (data.text !== undefined && data.text !== null) {
      if (data.mode === "replace") {
        output.textContent = applyTerminalControlText("", data.text);
      } else {
        output.textContent = applyTerminalControlText(output.textContent, data.text);
      }
    }

    output.scrollTop = output.scrollHeight;
  }

  function renderTerminal(data, fallbackMessage = "") {
    const { panel, status, output } = terminalElements();
    if (!panel || !output) return;

    const state = data.status === "success" ? "success" : "error";
    setTerminalStatus(status, state);

    if (data.terminal !== undefined && data.terminal !== null && String(data.terminal).trim()) {
      output.textContent = applyTerminalControlText("", data.terminal);
    } else {
      const message = data.message || fallbackMessage || "Command finished without terminal output.";
      output.textContent = applyTerminalControlText("", message);
    }

    output.scrollTop = output.scrollHeight;
  }

  function setSubmitDisabled(form, disabled) {
    const submitter = form.querySelector('button[type="submit"], input[type="submit"]');
    if (submitter) submitter.disabled = disabled;
  }

  async function runJsonCommand(payload) {
    const response = await fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    return response.json();
  }

  function dispatchStreamEvent(eventName, payload, streamState) {
    if (eventName === "terminal") {
      writeTerminalChunk(payload);
      return;
    }

    if (eventName === "status") {
      const { status } = terminalElements();
      setTerminalStatus(status, payload.status);
      return;
    }

    if (eventName === "done") {
      streamState.finalData = payload;
      const { status } = terminalElements();
      setTerminalStatus(status, payload.status === "success" ? "success" : "error");
    }
  }

  function processSseBlock(block, streamState) {
    let eventName = "message";
    const dataLines = [];

    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (!dataLines.length) return;

    const rawData = dataLines.join("\n");
    try {
      dispatchStreamEvent(eventName, JSON.parse(rawData), streamState);
    } catch (error) {
      writeTerminalChunk({
        mode: "append",
        status: "error",
        text: `\n[stream parse error] ${error.message || error}\n${rawData}\n`,
      });
    }
  }

  async function runStreamingCommand(payload) {
    const response = await fetch("/run/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Streaming request failed with HTTP ${response.status}`);
    }
    if (!response.body) {
      throw new Error("This browser does not expose a readable response stream.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const streamState = { finalData: null };
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        if (block.trim()) {
          processSseBlock(block, streamState);
        }
      }

      if (done) break;
    }

    if (buffer.trim()) {
      processSseBlock(buffer, streamState);
    }

    return streamState.finalData || {
      status: "error",
      message: "Streaming command ended before a final status was received.",
    };
  }

  async function submitForm(event) {
    event.preventDefault();
    const form = event.target;

    window.GONet?.extract?.updateCombinedFields?.(document);
    const payload = payloadFromForm(form);

    startTerminal(payload);
    setSubmitDisabled(form, true);

    try {
      const data = hasTerminalPanel()
        ? await runStreamingCommand(payload)
        : await runJsonCommand(payload);

      renderOutput(data);
      if (!hasTerminalPanel()) {
        renderTerminal(data);
      }

      // Only persist if the command actually ran successfully
      if (data.status === "success") {
        if (window.GONet?.cache?.saveCachedInputs) {
          window.GONet.cache.saveCachedInputs(form);
        }
      }
    } catch (error) {
      const message = `Request failed: ${error.message || error}`;
      const data = {
        status: "error",
        message,
        terminal: `ERROR: ${message}`,
      };
      renderOutput(data);
      if (hasTerminalPanel()) {
        writeTerminalChunk({ mode: "append", status: "error", text: `\nERROR: ${message}` });
      } else {
        renderTerminal(data);
      }
    } finally {
      setSubmitDisabled(form, false);
    }
  }

  // Export public API (only)
  window.GONet = window.GONet || {};
  window.GONet.forms = { submitForm };
})();
