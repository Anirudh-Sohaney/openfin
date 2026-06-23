/* ═══════════════════════════════════════════════════════════════════════════
   OpenFin Webapp — API Client
   Centralized fetch() calls to all backend REST endpoints
   ═══════════════════════════════════════════════════════════════════════════ */

const API_BASE = '/api';

/**
 * Generic fetch wrapper with error handling and timeout.
 * @param {string} path - API path (e.g., '/reports')
 * @param {object} options - Fetch options
 * @param {number} timeout - Timeout in ms (default 10000)
 * @returns {Promise<any>} Parsed JSON response
 */
async function apiFetch(path, options = {}, timeout = 10000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    try {
        const res = await fetch(`${API_BASE}${path}`, {
            ...options,
            signal: controller.signal,
            headers: {
                ...(options.body && !(options.body instanceof FormData)
                    ? { 'Content-Type': 'application/json' }
                    : {}),
                ...options.headers,
            },
        });
        clearTimeout(timer);

        if (!res.ok) {
            let detail = '';
            try {
                const err = await res.json();
                detail = err.detail || err.error || '';
            } catch (_) {}
            throw new Error(`HTTP ${res.status}: ${detail || res.statusText}`);
        }

        // Check if response is JSON
        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            return res.json();
        }
        return res;
    } catch (err) {
        clearTimeout(timer);
        if (err.name === 'AbortError') {
            throw new Error('Request timed out. Please check your connection and try again.');
        }
        throw err;
    }
}

/**
 * Fetch all reports from the API.
 * @returns {Promise<Array>} Array of report objects
 */
async function fetchReports() {
    return apiFetch('/reports');
}

/**
 * Fetch all insights from the API.
 * @returns {Promise<Array>} Array of insight objects
 */
async function fetchInsights() {
    return apiFetch('/insights');
}

/**
 * Fetch a report PDF file as a blob.
 * @param {string} filename - The PDF filename
 * @returns {Promise<Blob>} PDF blob
 */
async function fetchReportPdf(filename) {
    const res = await apiFetch(`/reports/${encodeURIComponent(filename)}`, {}, 30000);
    return res.blob();
}

/**
 * Fetch an insight PDF file as a blob.
 * @param {string} filename - The PDF filename
 * @returns {Promise<Blob>} PDF blob
 */
async function fetchInsightPdf(filename) {
    const res = await apiFetch(`/insights/${encodeURIComponent(filename)}`, {}, 30000);
    return res.blob();
}

/**
 * Delete a report PDF and its source JSON.
 * @param {string} filename - The PDF filename to delete
 * @returns {Promise<object>} Success response
 */
async function deleteReport(filename) {
    return apiFetch(`/reports/${encodeURIComponent(filename)}`, { method: 'DELETE' });
}

/**
 * Delete an insight PDF and its source JSON.
 * @param {string} filename - The PDF filename to delete
 * @returns {Promise<object>} Success response
 */
async function deleteInsight(filename) {
    return apiFetch(`/insights/${encodeURIComponent(filename)}`, { method: 'DELETE' });
}

/**
 * Upload a data file to trigger Agent 1 pipeline.
 * @param {File} file - The file to upload
 * @returns {Promise<object>} Upload response with success status
 */
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    return apiFetch('/upload', {
        method: 'POST',
        body: formData,
    }, 60000);
}

/**
 * Send a chat prompt to Agent 2.
 * @param {string} prompt - User's question
 * @param {Array} history - Conversation history (last 2-4 exchanges)
 * @returns {Promise<object>} Response with answer and optional caveats
 */
async function sendChat(prompt, history = []) {
    return apiFetch('/chat', {
        method: 'POST',
        body: JSON.stringify({ prompt, history }),
    }, 120000);
}

/**
 * Fetch current agent/subagent activity statuses.
 * @returns {Promise<object>} Agent status object
 */
async function fetchAgentStatus() {
    return apiFetch('/agents/status');
}

/**
 * Fetch current configuration (keys masked).
 * @returns {Promise<object>} Config object
 */
async function fetchConfig() {
    return apiFetch('/config');
}

/**
 * Save configuration values.
 * @param {object} config - Config fields to update
 * @returns {Promise<object>} Success response
 */
async function saveConfig(config) {
    return apiFetch('/config', {
        method: 'POST',
        body: JSON.stringify(config),
    });
}

/**
 * Check server health.
 * @returns {Promise<object>} Health status
 */
async function fetchHealth() {
    return apiFetch('/health', {}, 5000);
}
