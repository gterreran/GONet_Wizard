function loadForm(command) {
    fetch('/form/' + command).then(r => r.text()).then(html => {
      const form = document.getElementById('args-form');
      form.innerHTML = html;
  
      const hidden = document.createElement('input');
      hidden.type = 'hidden';
      hidden.name = 'command';
      hidden.value = command;
      form.appendChild(hidden);
    });
  }
  
  function submitForm(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const payload = Object.fromEntries(formData.entries());
    fetch('/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
      document.getElementById('output').textContent = data.message;
    });
  }
  
  // Optional: modal control (for exit confirmation)
  function showExitModal() {
    document.getElementById('exit-modal').classList.remove('hidden');
  }
  
  function closeExitModal() {
    document.getElementById('exit-modal').classList.add('hidden');
  }