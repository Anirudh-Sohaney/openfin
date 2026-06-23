/* ═══════════════════════════════════════════════════════════════════════════
   OpenFin Webapp — Config Page Logic
   Provider selection, API key management, lock/change mechanism
   ═══════════════════════════════════════════════════════════════════════════ */

// Provider base URLs for display
const PROVIDER_BASE_URLS = {
    openai:     "https://api.openai.com/v1",
    anthropic:  "https://api.anthropic.com/v1",
    gemini:     "https://generativelanguage.googleapis.com/v1beta",
    openrouter: "https://openrouter.ai/api/v1",
    xai:        "https://api.x.ai/v1",
    deepseek:   "https://api.deepseek.com/v1",
    groq:       "https://api.groq.com/openai/v1",
    together:   "https://api.together.xyz/v1",
    mistral:    "https://api.mistral.ai/v1",
};

/**
 * Initialize the config page.
 */
async function initConfig() {
    setupThemeToggle();
    await loadConfigValues();

    // Provider dropdown change → update base URL display
    const provSelect = document.getElementById('configProvider');
    if (provSelect) {
        provSelect.addEventListener('change', () => updateBaseUrlDisplay());
    }

    // Change buttons
    document.getElementById('llmKeyChangeBtn')?.addEventListener('click', () => unlockField('llmkey'));
    document.getElementById('tavilyChangeBtn')?.addEventListener('click', () => unlockField('tavily'));
}

/**
 * Set up the theme toggle buttons.
 */
function setupThemeToggle() {
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const theme = btn.dataset.themeVal;
            setTheme(theme);
        });
    });
}

/**
 * Set the theme (dark/light) and persist to localStorage.
 */
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('openfin-theme', theme);

    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-theme-val') === theme);
    });
}

/**
 * Update the base URL display when provider changes.
 */
function updateBaseUrlDisplay() {
    const provSelect = document.getElementById('configProvider');
    const baseUrlEl = document.getElementById('llmBaseUrl');
    const provider = provSelect.value;

    if (provider && PROVIDER_BASE_URLS[provider]) {
        baseUrlEl.textContent = `Base URL: ${PROVIDER_BASE_URLS[provider]}`;
    } else {
        baseUrlEl.textContent = 'Base URL: —';
    }
}

/**
 * Unlock a locked field for editing (triggered by Change button).
 */
function unlockField(type) {
    const row = document.getElementById(`${type}-row`);
    if (!row) return;

    const input = row.querySelector('input');
    const changeBtn = row.querySelector('.config-change-btn');

    if (input) {
        input.disabled = false;
        input.value = '';
        input.focus();
    }
    if (changeBtn) {
        changeBtn.style.display = 'none';
    }
}

/**
 * Lock a field after saving (hide key, disable input, show Change button).
 */
function lockField(type, maskedValue) {
    const row = document.getElementById(`${type}-row`);
    if (!row) return;

    const input = row.querySelector('input');
    const changeBtn = row.querySelector('.config-change-btn');

    if (input) {
        input.value = maskedValue || '';
        input.disabled = true;
    }
    if (changeBtn) {
        changeBtn.style.display = '';
    }
}

/**
 * Load config values from the server and populate form fields.
 * Locks fields that have values already saved.
 */
async function loadConfigValues() {
    try {
        const config = await fetchConfig();

        // Provider dropdown
        const provSelect = document.getElementById('configProvider');
        if (provSelect && config.provider) {
            provSelect.value = config.provider;
        }

        // LLM API Key
        const llmInput = document.getElementById('configLlmKey');
        if (llmInput) {
            if (config.llm_key) {
                // Has saved key — lock it
                lockField('llmkey', config.llm_key);
            } else {
                // No saved key — leave unlocked
                llmInput.disabled = false;
                document.getElementById('llmKeyChangeBtn').style.display = 'none';
            }
        }

        // Tavily key
        const tavilyInput = document.getElementById('configTavily');
        if (tavilyInput) {
            if (config.tavily_key) {
                lockField('tavily', config.tavily_key);
            } else {
                tavilyInput.disabled = false;
                document.getElementById('tavilyChangeBtn').style.display = 'none';
            }
        }

        // Model
        const modelInput = document.getElementById('configModel');
        if (modelInput) {
            if (config.llm_model) {
                modelInput.value = config.llm_model;
                modelInput.disabled = true;
            } else {
                modelInput.disabled = false;
            }
        }

        // Update base URL display
        updateBaseUrlDisplay();
    } catch (err) {
        console.warn('Failed to load config:', err.message);
    }
}

/**
 * Save config values from the form to the server.
 */
async function saveConfigValues() {
    const statusEl = document.getElementById('configStatus');
    statusEl.textContent = 'Saving...';
    statusEl.className = 'config-status';

    const config = {};

    // Provider
    const provSelect = document.getElementById('configProvider');
    if (provSelect) {
        const val = provSelect.value.trim();
        if (val) {
            config.provider = val;
        }
    }

    // LLM API Key — only include if field is unlocked (being changed)
    const llmInput = document.getElementById('configLlmKey');
    if (llmInput && !llmInput.disabled && llmInput.value.trim()) {
        config.llm_key = llmInput.value.trim();
    }

    // Tavily key — only include if field is unlocked
    const tavilyInput = document.getElementById('configTavily');
    if (tavilyInput && !tavilyInput.disabled && tavilyInput.value.trim()) {
        config.tavily_key = tavilyInput.value.trim();
    }

    // Model — only include if field is unlocked (first time) or always include if changed
    const modelInput = document.getElementById('configModel');
    if (modelInput && !modelInput.disabled && modelInput.value.trim()) {
        config.llm_model = modelInput.value.trim();
    }

    // Validate: need at least a provider if providing LLM key
    if (config.llm_key && !config.provider) {
        statusEl.textContent = 'Please select an LLM provider first.';
        statusEl.className = 'config-status error';
        return;
    }

    try {
        await saveConfig(config);
        statusEl.textContent = 'Settings saved successfully.';
        statusEl.className = 'config-status success';

        // Reload to update lock states and show masked values
        await loadConfigValues();

        setTimeout(() => { statusEl.textContent = ''; }, 3000);
    } catch (err) {
        statusEl.textContent = `Failed to save: ${err.message}`;
        statusEl.className = 'config-status error';
    }
}

/**
 * Initialize the theme on page load from localStorage.
 */
function initTheme() {
    const savedTheme = localStorage.getItem('openfin-theme') || 'dark';
    setTheme(savedTheme);
}
