/* ═══════════════════════════════════════════════════════════════════════════
   OpenFin Webapp — Sidebar Agent Status
   Polls GET /api/agents/status and updates sidebar DOM in real-time
   ═══════════════════════════════════════════════════════════════════════════ */

class SidebarStatus {
    constructor() {
        this.pollInterval = null;
    }

    /**
     * Start polling agent status every 3 seconds.
     */
    start() {
        if (this.pollInterval) return;
        this.idleCount = 0;
        this.pollInterval = setInterval(() => this._poll(), 3000);
        // Initial poll
        this._poll();
    }

    /**
     * Stop polling agent status.
     */
    stop() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.idleCount = 0;
    }

    /**
     * Perform a single poll of agent status.
     */
    async _poll() {
        try {
            const status = await fetchAgentStatus();
            this._updateUI(status);
        } catch (err) {
            // Silently handle errors — sidebar status is non-critical
            console.warn('Sidebar poll error:', err.message);
        }
    }

    /**
     * Check if all subagents are idle.
     */
    _allIdle(status) {
        for (const agent of Object.values(status)) {
            for (const activity of Object.values(agent)) {
                if (activity !== 'idle' && activity !== 'unknown') {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * Update sidebar DOM elements with current status.
     * Matches subagents by parent agent group to prevent cross-agent name collisions.
     */
    _updateUI(status) {
        // Update each subagent's status element
        document.querySelectorAll('.agent').forEach(agentEl => {
            // Determine which agent this group is (Agent 1 or Agent 2)
            const headingEl = agentEl.querySelector('.agent-heading');
            if (!headingEl) return;
            const agentName = headingEl.textContent.trim();

            // Get the status data for this agent
            const subagentData = status[agentName];
            if (!subagentData) return;

            // Update each subagent within this agent group
            agentEl.querySelectorAll('.subagent').forEach(el => {
                const nameEl = el.querySelector('.subagent-name');
                const statusEl = el.querySelector('.status');
                if (!nameEl || !statusEl) return;

                const subName = nameEl.textContent.trim();
                const activity = subagentData[subName] || 'unknown';

                // Update text
                statusEl.textContent = activity;

                // Update dot indicator
                const dot = statusEl.querySelector('.status-dot') || (() => {
                    const d = document.createElement('span');
                    d.className = 'status-dot';
                    statusEl.prepend(d);
                    return d;
                })();

                dot.className = 'status-dot';
                if (activity === 'idle' || activity === 'unknown') {
                    dot.classList.add('idle');
                } else {
                    dot.classList.add('active');
                }
            });
        });
    }
}

// Global singleton
const sidebarStatus = new SidebarStatus();
