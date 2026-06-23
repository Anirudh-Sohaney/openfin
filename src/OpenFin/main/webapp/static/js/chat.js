/* ═══════════════════════════════════════════════════════════════════════════
   OpenFin Webapp — Chat Interface
   Manages conversation history, sending messages, receiving Agent 2 responses
   ═══════════════════════════════════════════════════════════════════════════ */

class ChatInterface {
    constructor() {
        this.history = [];
        this.isProcessing = false;
        this.MAX_HISTORY = 4; // Keep last 4 exchanges
    }

    /**
     * Initialize the chat interface.
     */
    init() {
        this.inputEl = document.getElementById('chatInput');
        this.msgsEl = document.getElementById('chatMsgs');
        this.sendBtn = document.getElementById('chatSendBtn');

        // Event listeners
        this.inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.send();
            }
        });
        this.sendBtn.addEventListener('click', () => this.send());

        // Clear conversation button
        const clearBtn = document.getElementById('chatClearBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clear());
        }
    }

    /**
     * Send the current input as a message to Agent 2.
     */
    async send() {
        const text = this.inputEl.value.trim();
        if (!text || this.isProcessing) return;

        // Add user message to UI
        this._addMessage(text, 'user');
        this.inputEl.value = '';

        // Ensure sidebar polling is active to show Agent 2 subagent activity
        sidebarStatus.start();

        // Show typing indicator
        this._showTyping();
        this.isProcessing = true;
        this._setInputState(false);

        try {
            const response = await sendChat(text, this.history);

            // Remove typing indicator
            this._hideTyping();

            // Add bot message
            const answer = response.answer || 'No response received.';
            const caveats = response.caveats || '';
            this._addMessage(answer, 'bot', caveats);

            // Store in history
            this.history.push(
                { role: 'user', content: text },
                { role: 'assistant', content: answer }
            );

            // Trim history to max exchanges
            if (this.history.length > this.MAX_HISTORY * 2) {
                this.history = this.history.slice(-this.MAX_HISTORY * 2);
            }
        } catch (err) {
            this._hideTyping();
            this._addMessage(`Error: ${err.message}`, 'bot', 'Please try again or check your connection.');
        } finally {
            this.isProcessing = false;
            this._setInputState(true);
            this.inputEl.focus();
        }
    }

    /**
     * Clear conversation history and UI.
     */
    async clear() {
        this.history = [];
        this.msgsEl.innerHTML = '';
        // Reset conversation on server side too
        try {
            await apiFetch('/chat/reset', { method: 'POST' });
        } catch (_) {}
        this._addMessage(
            "Hello! I'm OpenFin's financial advisor. Ask me anything about your data.",
            'bot'
        );
    }

    /**
     * Add a message to the chat UI.
     */
    _addMessage(text, role, caveat) {
        const msg = document.createElement('div');
        msg.className = `msg msg-${role}`;

        const textEl = document.createElement('div');
        textEl.textContent = text;
        msg.appendChild(textEl);

        if (caveat) {
            const caveatEl = document.createElement('div');
            caveatEl.className = 'msg-caveat';
            caveatEl.textContent = caveat;
            msg.appendChild(caveatEl);
        }

        this.msgsEl.appendChild(msg);
        this._scrollToBottom();
    }

    /**
     * Show the typing indicator.
     */
    _showTyping() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.id = 'typingIndicator';
        indicator.innerHTML = '<span>.</span><span>.</span><span>.</span>';
        this.msgsEl.appendChild(indicator);
        this._scrollToBottom();
    }

    /**
     * Hide the typing indicator.
     */
    _hideTyping() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Enable/disable input controls.
     */
    _setInputState(enabled) {
        this.inputEl.disabled = !enabled;
        this.sendBtn.disabled = !enabled;
    }

    /**
     * Scroll chat to the bottom.
     */
    _scrollToBottom() {
        this.msgsEl.scrollTop = this.msgsEl.scrollHeight;
    }
}

// Global singleton
const chatInterface = new ChatInterface();
