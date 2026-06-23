/* ═══════════════════════════════════════════════════════════════════════════
   OpenFin Webapp — PDF Preview Modal
   Handles opening, closing, downloading PDFs in a modal overlay
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Open the PDF preview modal for a given file.
 * @param {string} filename - PDF filename
 * @param {string} type - 'reports' or 'insights'
 * @param {string} description - Short description of the file
 */
async function openPdfModal(filename, type, description) {
    const modal = document.getElementById('pdfModal');
    const titleEl = document.getElementById('modalTitle');
    const bodyEl = document.getElementById('modalBody');

    // Set metadata
    titleEl.textContent = filename;
    modal.dataset.filename = filename;
    modal.dataset.type = type;

    // Show loading state
    bodyEl.innerHTML = `
        <div class="modal-loading">
            <div class="spinner"></div>
            <span>Loading PDF...</span>
        </div>
    `;

    modal.classList.add('open');

    try {
        // Fetch the PDF blob
        const blob = type === 'reports'
            ? await fetchReportPdf(filename)
            : await fetchInsightPdf(filename);

        // Create an object URL and embed the PDF
        const url = URL.createObjectURL(blob);
        bodyEl.innerHTML = `
            <iframe src="${url}" 
                    width="100%" height="100%" 
                    style="border:none;"
                    title="${escapeHtml(filename)}">
            </iframe>
        `;
    } catch (err) {
        // Fallback: show terminal-styled placeholder
        const typeLabel = type === 'reports' ? 'Report' : 'Insight';
        bodyEl.innerHTML = `
            <div class="pdf-preview">
                <div class="pdf-placeholder">
                    <div class="pdf-line hl">&gt; OpenFin ${typeLabel} Viewer</div>
                    <div class="pdf-line">&gt; File: <span id="pdfFileName">${escapeHtml(filename)}</span></div>
                    <div class="pdf-line">&gt; Type: <span>${typeLabel}</span></div>
                    <div class="pdf-line">&gt; Description: ${escapeHtml(description || 'N/A')}</div>
                    <div class="pdf-line">&gt; </div>
                    <div class="pdf-line">&gt; Could not render PDF preview.</div>
                    <div class="pdf-line">&gt; Please use Download to view the file.</div>
                    <div class="pdf-line">&gt; Error: ${escapeHtml(err.message)}</div>
                    <div class="pdf-line">&gt; </div>
                    <div class="pdf-line hl">&gt; [ End of Preview ]</div>
                </div>
            </div>
        `;
    }
}

/**
 * Close the PDF preview modal.
 */
function closePdfModal() {
    const modal = document.getElementById('pdfModal');
    modal.classList.remove('open');

    // Clean up object URLs from iframes
    const iframe = modal.querySelector('iframe');
    if (iframe) {
        URL.revokeObjectURL(iframe.src);
    }
}

/**
 * Download the currently displayed PDF.
 */
async function downloadPdf() {
    const modal = document.getElementById('pdfModal');
    const filename = modal.dataset.filename;
    const type = modal.dataset.type;
    if (!filename) return;

    try {
        const blob = type === 'reports'
            ? await fetchReportPdf(filename)
            : await fetchInsightPdf(filename);

        // Create download link and click it
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
        alert(`Download failed: ${err.message}`);
    }
}

