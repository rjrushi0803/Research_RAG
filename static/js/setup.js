// Setup wizard — step navigation and provider selection

function nextStep(step) {
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.step-dot').forEach(d => {
        const ds = parseInt(d.dataset.step);
        d.classList.remove('active');
        if (ds < step) d.classList.add('completed');
        else d.classList.remove('completed');
    });
    const target = document.querySelector(`.step[data-step="${step}"]`);
    if (target) target.classList.add('active');
    const dot = document.querySelector(`.step-dot[data-step="${step}"]`);
    if (dot) dot.classList.add('active');
}

function selectProvider(provider) {
    document.querySelectorAll('.provider-card').forEach(c => c.classList.remove('selected'));
    const card = document.querySelector(`.provider-card[data-provider="${provider}"]`);
    if (card) card.classList.add('selected');

    document.getElementById('llmProvider').value = provider;

    const apiGroup = document.getElementById('apiKeyGroup');
    const ollamaGroup = document.getElementById('ollamaGroup');

    if (provider === 'ollama') {
        if (apiGroup) apiGroup.classList.add('hidden');
        if (ollamaGroup) ollamaGroup.classList.remove('hidden');
        fetchOllamaModels();
    } else {
        if (apiGroup) apiGroup.classList.remove('hidden');
        if (ollamaGroup) ollamaGroup.classList.add('hidden');
    }
}

function fetchOllamaModels() {
    const container = document.getElementById('ollamaModels');
    if (!container) return;
    container.innerHTML = '<div class="flex-center"><div class="spinner"></div></div>';

    fetch('/api/ollama-models')
        .then(r => r.json())
        .then(data => {
            if (data.models && data.models.length > 0) {
                let html = '<label class="form-label">Detected Models</label><div class="source-toggles">';
                data.models.forEach(m => {
                    html += `<label class="source-toggle" onclick="document.getElementById('modelNameInput').value='${m}'">
                        <span>🦙 ${m}</span></label>`;
                });
                html += '</div>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<div class="alert alert-warning">No Ollama models detected. Make sure Ollama is running.</div>';
            }
        })
        .catch(() => {
            container.innerHTML = '<div class="alert alert-warning">Could not connect to Ollama.</div>';
        });
}

// Source toggle styling
document.querySelectorAll('.source-toggle input').forEach(cb => {
    cb.addEventListener('change', function() {
        this.closest('.source-toggle').classList.toggle('active', this.checked);

        if (this.value === 'core') {
            const coreGroup = document.getElementById('coreKeyGroup');
            if (coreGroup) coreGroup.style.display = this.checked ? 'block' : 'none';
        }
    });
});
