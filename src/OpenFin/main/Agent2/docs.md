# Agent 2 — Directory Documentation

## Key Objective
Serve as a financial advisor and chatbot, providing quick, data-backed answers to user prompts based on filtered-data, reports, and online research. Agent 2 operates on-demand per user prompt (no file monitoring).

## Key Initiating Function / Call Process

```python
from main.Agent2.main import run

answer = run("what is my annual revenue?")
# Returns: "Your total annual revenue is $2,678,346.14..."
```

The orchestrator in `main.py` coordinates the pipeline:

```
run(prompt)
  ├── subAgent 1: Analyze prompt → retrieve data from local files or Tavily
  ├── Inject conversation memory (2-4 prior exchanges)
  ├── subAgent 2: Generate professional response via LLM
  └── Return answer string
```

## Major Files

| File | Purpose |
|------|---------|
| `main.py` | Orchestrator — coordinates subAgents, manages conversation memory, returns string answer |
| `specs.md` | Key objectives and structure for Agent 2 |
| `subAgent1/main.py` | Prompt analysis + data retrieval pipeline |
| `subAgent2/main.py` | LLM-based response generation pipeline |

## Data Sources

| Source | Format | Path | Content |
|--------|--------|------|---------|
| `filtered-data` | JSON | `main/data/filtered-data/` | Structured financial metrics (revenue, sales, expenses, growth rates) |
| `base-reports` | PDF | `main/reports/base-reports/` | Narrative financial reports (Revenue, P&L, Financial Health) |
| `insights` | PDF | `main/reports/insights/` | Research-driven analysis (pricing, cost reduction, risk assessment) |
| `internet` | Web | Tavily API | Live search for external information (suppliers, competitors, trends) |

## Conversation Memory

Agent 2 maintains a sliding window of up to 4 prior exchanges. Each exchange stores the user's question, the advisor's answer, and the data source used. This context is injected into subAgent 2's LLM prompt, enabling coherent multi-turn conversations.

## Tools / Algorithms Used
- **OpenRouter API (gpt-oss-120b:free)**: subAgent 1's prompt analysis (1 LLM call) + subAgent 2's response generation (1 LLM call).
- **pypdf (v6.x)**: Extracts text from PDF reports.
- **Tavily API**: Web search for external/market research.
- **Keyword frequency scoring**: Ranks documents by keyword relevance.
- **ConversationMemory**: Sliding-window history for multi-turn context.
- **Activity logging**: Timestamped logs in `log.txt`.
