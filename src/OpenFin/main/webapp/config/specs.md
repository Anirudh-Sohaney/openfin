OpenFin Webapp — Config Page

________________________________________________________________________________________________________________________________________

Key Objective :

    Allow the user to customize the webapp appearance and manage backend API credentials. Settings are persisted server-side in a config file and client-side for theme preference.

________________________________________________________________________________________________________________________________________

Configuration Storage :

    Server-side : webapp/config/config.json
        - Stores provider, LLM API key, model, and Tavily API key
        - Read by the API bridge when initializing Agent 1 and Agent 2
        - Never exposed to the frontend in plain text on list endpoints

    Client-side : localStorage
        - Stores theme preference (dark/light)
        - Applied on page load before server config is fetched
        - Allows instant theme switching without server round trip

________________________________________________________________________________________________________________________________________

Page Layout :

    - Page header (in the main page-header bar): "← Config"
    - Content area: vertical form layout, max-width ~420px
    - Each config item is a label above its control
    - Items grouped by category with spacing

________________________________________________________________________________________________________________________________________

Config Items :

    Theme :
        - Toggle between Dark and Light mode
        - Two buttons: "Dark" | "Light"
        - Active button highlighted with accent color border
        - Clicking a button immediately switches the theme via CSS data-theme attribute
        - Preference saved to localStorage

    LLM Provider :
        - Dropdown select with options: OpenAI, Anthropic, Google Gemini, OpenRouter, xAI, DeepSeek, Groq, Together AI, Mistral AI
        - Selections updates the displayed base URL below the API key field
        - Sent to POST /api/config as "provider"

    LLM API Key :
        - Password input field (masked)
        - Placeholder: "Enter your API key..."
        - Locked with a "Change" button if a key is already saved
        - On save, sent to POST /api/config as "llm_key"
        - Stored in server-side config.json
        - Used by Agent 1 and Agent 2 for LLM calls

    Tavily API Key :
        - Password input field (masked)
        - Placeholder: "tvly-..."
        - On save, sent to POST /api/config
        - Stored in server-side config.json
        - Used by Agent 1's subAgent 3 for online research

    LLM Model :
        - Read-only text field (disabled)
        - Displays the current model selection: "owl alpha / gpt oss 120b"
        - Updated via config.json if model changes in the future

________________________________________________________________________________________________________________________________________

Functionality :

    Loading Config :
        - On page load (or navigation to Config page), frontend calls GET /api/config
        - Returns: { "provider": "openrouter", "llm_key": "sk-or-... (masked)", "llm_model": "...", "tavily_key": "tvly-... (masked)" }
        - Keys are masked (show last 4 characters, rest asterisks) for security
        - Theme is loaded from localStorage (client-side only)

    Saving Config :
        - User modifies a field and clicks "Save" (or changes are auto-saved on blur)
        - Frontend sends POST /api/config with the updated values
        - API bridge writes to webapp/config/config.json
        - Returns success confirmation
        - On failure, show error message with retry option

    Validation :
        - API key fields validate format before sending (starts with expected prefix)
        - Invalid keys show inline error message
        - Empty keys are allowed (shows warning: "Some features may not work without API keys")

________________________________________________________________________________________________________________________________________

API Endpoints Used :

    GET  /api/config    Retrieve current config (keys masked)
    POST /api/config    Update config values

________________________________________________________________________________________________________________________________________

Key Notes :

    - API keys must never be logged or exposed in error messages
    - Config file should have restricted file permissions (readable only by the webapp process)
    - Theme preference is client-only; no server-side theme storage needed
    - Consider adding a "Test Connection" button for each API key to verify validity
    - Default state (no config saved) should show empty fields with placeholder text
