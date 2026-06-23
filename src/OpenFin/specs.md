# OpenFin — Specifications

## Overview

OpenFin is a multi-agent financial analysis platform that automates the generation of financial reports, insights, and interactive Q&A from uploaded data (CSV/XLSX). The system is composed of two main agents, each with specialized subagents, and a web frontend.

## Architecture

```
User Upload (CSV/XLSX)
        |
        v
  Agent 1 — Financial Pipeline
    ├── subAgent 1 — Data Loader & Metrics Calculator
    ├── subAgent 2 — Base Report Generator
    ├── subAgent 3 — Research & Insights Generator
    ├── subAgent 4 — Financial Issue Analyzer
    └── subAgent 5 — PDF Report Generator
        |
        v
  JSON Reports → PDF Reports → Web UI / API
        ^
        |
  Agent 2 — Q&A Chatbot
    ├── subAgent 1 — Prompt Analyzer & Data Retriever
    └── subAgent 2 — Response Generator
```

## Agent 1 — Financial Pipeline

Agent 1 is the core data processing engine. It is triggered when new data files are uploaded.

### Pipeline Flow

1. **subAgent 1** loads the uploaded CSV/XLSX, uses an LLM to identify column mappings, calculates financial metrics, and saves filtered data to `main/data/filtered-data/`.
2. **subAgent 2** loads filtered metrics, identifies which base report types can be generated, and produces JSON reports in `main/Agent1/base-gens/`.
3. **subAgent 3** performs market research via web search (Tavily API) and generates insight reports in `main/Agent1/insight-gens/`.
4. **subAgent 4** analyzes financial data for issues and inefficiencies, generating diagnostic reports in `main/Agent1/insight-gens/`.
5. **subAgent 5** watches for new JSON reports and converts them to PDFs in `main/reports/`.

## Agent 2 — Q&A Chatbot

Agent 2 provides a conversational interface for querying financial data and reports. It uses the LLM to interpret user prompts, retrieves relevant data, and generates natural-language responses.

## Technology Stack

- **Language:** Python 3.12
- **Web Server:** Python `http.server` (ThreadingHTTPServer)
- **Frontend:** Vanilla HTML/CSS/JS SPA
- **LLM Integration:** Multi-provider client supporting OpenAI, Anthropic, Gemini, OpenRouter, xAI, DeepSeek, Groq, Together AI, Mistral
- **Search:** Tavily API for web research
- **PDF Generation:** ReportLab
- **Data Format:** JSON for intermediate data, PDF for final reports

## Environment Variables

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | LLM provider name (e.g., openai, anthropic) |
| `LLM_API_KEY` | API key for the LLM provider |
| `LLM_MODEL` | Model identifier string |
| `LLM_BASE_URL` | Base URL for the LLM API |
| `TAVILY_API_KEY` | API key for Tavily web search |
