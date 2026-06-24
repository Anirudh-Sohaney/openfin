# OpenFin

A local, multi-agent financial analysis platform. Upload financial data (CSV/XLSX) and get automated reports, insights, and an interactive Q&A chatbot — all running locally on your machine.

---

## Setup

**Prerequisites:** [uv](https://docs.astral.sh/uv/) must be installed.

```bash
uv tool install git+https://github.com/Anirudh-Sohaney/openfin.git
```

After installation finishes, start the server:

```bash
openfin
```

Wait for the server to start, then open **https://localhost:6161**.

## Configuration

1. On the home page, click the **Config** button.
2. Set your **LLM provider** (OpenAI, Anthropic, Google Gemini, OpenRouter, xAI, DeepSeek, Groq, Together AI, or Mistral AI).
3. Enter your **LLM API key** and **Tavily API key** (required for web research).
4. Click **Save Changes**.

The server persists these settings in `webapp/config/config.json`. You can change them anytime.

## Usage

### Upload Data

On the home page, click **Upload File** and select your financial data (CSV format). Once uploaded, the agents appear in the left sidebar and begin processing.

### Base Reports

After uploading, wait 15–120 seconds (depending on your LLM provider and data size), then click the **Reports** button. Basic financial reports — revenue, sales, profit & loss, expense, cash flow, inventory, and more — will load. Each report includes professional summaries, evidence, analysis, and recommendations.

### Insights

Roughly 60 seconds after upload, click the **Insights** button. Insight reports — such as alternative supplier analysis, potential product opportunities, and financial inefficiencies — will load. Each includes internet research, evidence, and recommendations.

### Agent 2 — Q&A Chatbot

Once Agent 1's subAgent 1 shows **"idle"** in the sidebar (30–600 seconds depending on LLM and data size), click the **Agent** button to open the chatbot. Ask questions about your uploaded data, reports, or insights — the chatbot retrieves relevant information and responds with data-backed answers.

---

## Directory Structure

```
src/
  OpenFin/                         # Package root
    cli.py                         # CLI entry point (openfin command)
    specs.md                       # Top-level specifications

    main/
      __init__.py
      llm_client.py                # Multi-provider LLM abstraction layer

      data/
        uploaded-data/             # Raw user uploads (CSV/XLSX)
        filtered-data/             # Processed metrics from subAgent 1

      reports/
        base-reports/              # PDF base reports
        insights/                  # PDF insight reports

      Agent1/                      # Financial Pipeline Agent
        main.py                    # Orchestration logic
        specs.md / main.md / docs.md
        subAgent1/                 # Data Loader & Metrics Calculator
        subAgent2/                 # Base Report Generator
        subAgent3/                 # Research & Insights Generator
        subAgent4/                 # Financial Issue Analyzer
        subAgent5/                 # PDF Report Generator

      Agent2/                      # Q&A Chatbot Agent
        main.py                    # Orchestration logic
        specs.md / main.md / docs.md
        subAgent1/                 # Prompt Analyzer & Data Retriever
        subAgent2/                 # Response Generator

      webapp/
        server.py                  # HTTP server (ThreadingHTTPServer)
        index.html                 # Single-page application entry
        config/
          config.json              # Persisted API keys and provider
          specs.md
        static/
          css/                     # Stylesheets
          js/                      # Client-side JavaScript
```

Each agent and subagent directory contains its own `main.py` (implementation), `specs.md` (specification), `main.md` (design notes), and `docs.md` (documentation). SubAgents additionally contain module files (e.g., `data_loader.py`, `metrics_calculator.py`, `pdf_generator.py`) reflecting their internal components.

---

## Key Program Structure

### Agent 1 — Financial Pipeline

Orchestrates the end-to-end data processing pipeline. Upon detecting new uploaded files, it runs subAgent 1 first, then starts subAgent 5's watcher, and launches subAgents 2, 3, and 4 in parallel. Agent 1 does not make LLM calls itself — it delegates entirely to its subAgents and tracks their activity via log files.

- **subAgent 1** (Data Loader & Metrics Calculator): Loads CSV/XLSX files, sends column metadata to an LLM to identify what metrics can be derived, then computes financial metrics (revenue, margins, growth rates, turnover, etc.) across multiple timeframes (3–36 months) and saves structured results to `filtered-data/`.

- **subAgent 2** (Base Report Generator): Consults an LLM to identify which standard financial reports are possible given the available metrics, then iterates through each candidate report — reprompting the LLM with relevant data — and saves structured JSON reports (with Data, Analysis, and Conclusion sections) to `base-gens/`.

- **subAgent 3** (Research & Insights Generator): Evaluates key metrics against market data via the Tavily web search API to find profit-improvement opportunities — alternative suppliers, emerging products, pricing trends, cost reductions — and produces structured JSON insight reports saved to `insight-gens/`.

- **subAgent 4** (Financial Issue Analyzer): Scans derived metrics for financial inefficiencies and risks (declining margins, cash flow bottlenecks, concentration risk, excessive costs, etc.), generates diagnostic reports via the LLM with explanations and actionable advice, and saves them to `insight-gens/`.

- **subAgent 5** (PDF Report Generator): Watches `base-gens/` and `insight-gens/` for new JSON reports, converts each to a professionally formatted PDF using ReportLab (no LLM calls — purely algorithmic), and outputs to `reports/base-reports/` or `reports/insights/`.

### Agent 2 — Q&A Chatbot

Provides a conversational interface for querying uploaded data, reports, and insights. When a user prompt arrives, it delegates to subAgent 1 for analysis and data retrieval, then to subAgent 2 for response generation. Maintains 2–4 message conversational memory for context.

- **subAgent 1** (Prompt Analyzer & Data Retriever): Uses an LLM to parse the user's intent and identify the required data sources (filtered-data, base reports, insights, or web search via Tavily), retrieves the relevant information, and returns a structured context bundle to subAgent 2. Completes in under 2 LLM calls.

- **subAgent 2** (Response Generator): Receives subAgent 1's structured context and produces a comprehensive, data-backed natural-language response via a single LLM call. Cites sources, handles missing or conflicting data transparently, and maintains a professional financial advisory tone.

---

All code details, design rationale, and pipeline specifications are documented in `specs.md` files located throughout the codebase at each agent and subAgent level.
