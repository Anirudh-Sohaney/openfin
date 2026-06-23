/* ═══════════════════════════════════════════════════════════════════════════
   OpenFin Webapp — Main Application
   SPA router, navigation, page management, global event handlers
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Navigate to a page by name.
 * @param {string} page - Page name: 'home', 'reports', 'insights', 'chatbot', 'config'
 */
function navigate(page) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));

    // Show target page
    const target = document.getElementById(`page-${page}`);
    if (target) {
        target.classList.add('active');
    }

    // Update page header
    const header = document.getElementById('pageHeader');
    if (page === 'home') {
        header.classList.remove('visible');
    } else {
        header.classList.add('visible');
        const labels = {
            reports: 'Reports',
            insights: 'Insights',
            chatbot: 'Agent',
            config: 'Config'
        };
        document.getElementById('headerTitle').textContent = labels[page] || page;
    }

    // Page-specific initialization
    switch (page) {
        case 'reports':
            loadFileList('reports');
            break;
        case 'insights':
            loadFileList('insights');
            break;
        case 'chatbot':
            // Chat interface is already initialized
            break;
        case 'config':
            loadConfigValues();
            break;
    }
}

/**
 * Handle file upload via the upload button.
 */
function setupUploadButton() {
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const statusEl = document.getElementById('uploadStatus');

    uploadBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Validate file type
        const validTypes = ['.csv', '.xlsx', '.xls'];
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!validTypes.includes(ext)) {
            statusEl.textContent = 'Invalid file type. Please upload CSV, XLSX, or XLS files.';
            statusEl.className = 'upload-status error';
            return;
        }

        statusEl.textContent = 'Uploading...';
        statusEl.className = 'upload-status';

        try {
            const result = await uploadFile(file);
            statusEl.textContent = `File uploaded: ${result.filename}`;
            statusEl.className = 'upload-status success';
            // Start sidebar polling since agent pipeline may be running
            sidebarStatus.start();
        } catch (err) {
            statusEl.textContent = `Upload failed: ${err.message}`;
            statusEl.className = 'upload-status error';
        }

        // Reset file input
        fileInput.value = '';
    });
}

/**
 * Initialize the application when DOM is ready.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    initTheme();

    // Set up upload button
    setupUploadButton();

    // Initialize chat interface
    chatInterface.init();

    // Set up config save button
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    if (saveConfigBtn) {
        saveConfigBtn.addEventListener('click', saveConfigValues);
    }

    // Set up back arrow navigation
    document.querySelectorAll('.back-arrow').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            navigate('home');
        });
    });

    // Start sidebar polling for agent status
    sidebarStatus.start();

    // Initialize config page (theme toggle bindings, etc.)
    setupThemeToggle();

    // Load config values
    loadConfigValues();
});
