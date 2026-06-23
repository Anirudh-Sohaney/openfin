/* ═══════════════════════════════════════════════════════════════════════════
   OpenFin Webapp — File Card Component
   Renders file cards for Reports and Insights pages
   Handles click-to-open-modal and delete with confirmation
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Render a list of file cards into the given container.
 * @param {Array} files - Array of { name, description } objects
 * @param {string} type - 'reports' or 'insights'
 * @param {HTMLElement} container - DOM element to render into
 */
function renderFileCards(files, type, container) {
    container.innerHTML = '';

    if (!files || files.length === 0) {
        const message = type === 'reports'
            ? 'No reports generated yet. Upload data to get started.'
            : 'No insights generated yet. Upload data to get started.';
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📄</div>
                <div class="empty-text">${message}</div>
            </div>
        `;
        return;
    }

    files.forEach(file => {
        const card = document.createElement('div');
        card.className = 'file-card';
        card.dataset.name = file.name;
        card.dataset.type = type;

        card.innerHTML = `
            <div class="file-card-body">
                <div class="file-card-title">${escapeHtml(file.name.replace(/\.pdf$/i, ''))}</div>
                <div class="file-card-desc">${escapeHtml(file.description || 'No description available.')}</div>
            </div>
            <div class="file-card-delete">&times;</div>
        `;

        // Card click → open PDF preview
        card.addEventListener('click', (e) => {
            if (e.target.closest('.file-card-delete')) return;
            openPdfModal(file.name, type, file.description);
        });

        // Delete X → confirm + delete
        const deleteBtn = card.querySelector('.file-card-delete');
        deleteBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (!confirm(`Delete "${file.name}"? This will remove the PDF and its source data.`)) {
                return;
            }
            try {
                if (type === 'reports') {
                    await deleteReport(file.name);
                } else {
                    await deleteInsight(file.name);
                }
                // Animate removal
                card.classList.add('removing');
                setTimeout(() => card.remove(), 300);
            } catch (err) {
                alert(`Failed to delete: ${err.message}`);
            }
        });

        container.appendChild(card);
    });
}

/**
 * Escape HTML special characters to prevent XSS.
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Load files for a given page (reports or insights).
 * @param {string} type - 'reports' or 'insights'
 */
async function loadFileList(type) {
    const container = document.getElementById(`${type}-list`);
    if (!container) return;

    try {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon" style="opacity:0.5;font-size:1.5rem;">Loading...</div>
            </div>
        `;

        const files = type === 'reports' ? await fetchReports() : await fetchInsights();
        renderFileCards(files, type, container);
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-text">Failed to load ${type}: ${escapeHtml(err.message)}</div>
            </div>
        `;
    }
}
