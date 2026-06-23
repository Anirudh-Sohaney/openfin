# llm_interface.py

## Key Objective
Interfaces with an LLM via OpenRouter API to:
1. Identify which financial reports can be generated from available metrics
2. Generate detailed professional reports with Data, Analysis, and Conclusion sections

Falls back to heuristic pattern-matching when the LLM is unavailable.

## Tools / Algorithms Used
- **OpenRouter API**: Free model `openai/gpt-oss-120b:free` (configurable via `LLM_MODEL` env var) for intelligent report identification and detailed narrative generation. Includes `HTTP-Referer` and `X-Title` headers for OpenRouter ranking.
- **Heuristic fallback**: Pattern-matching on metric names against known report type requirements.
- **Metric categorization**: Groups metrics into categories (Revenue, Sales, Profit, Expense, Inventory, etc.) for structured LLM prompts.
- **JSON parsing with fallback**: Regex extraction of JSON from malformed LLM responses.

## Configuration (Environment Variables)
- `OPENAI_API_KEY` - Required. OpenRouter API key.
- `OPENAI_BASE_URL` - Base URL (default: `https://openrouter.ai/api/v1`).
- `LLM_MODEL` - Model name (default: `openai/gpt-oss-120b:free`). Supported free models also include `openrouter/owl-alpha`.

## Key Objects

### `KNOWN_REPORT_TYPES: list[str]`
- **Use**: Master list of 15 known financial report types from specs.md. Sent to the LLM as the universe of possible reports.

### `identify_possible_reports(all_metrics, existing_report_names) -> Dict`
- **Parameters**: `all_metrics` - list of metric dicts; `existing_report_names` - list of already generated report names.
- **Use**: Prompts the LLM to determine which reports can be generated. Returns `{"possible_reports": [...], "unavailable_reports": [...]}`.

### `generate_report(report_name, metrics, required_metrics, analysis_summary) -> Dict`
- **Parameters**: `report_name` - name of report to generate; `metrics` - full metrics dict; `required_metrics` - list of metric keys needed; `analysis_summary` - context from subAgent1.
- **Use**: Prompts the LLM to generate a detailed report with Data, Analysis, and Conclusion sections. Returns `{"Report Name": {"Section": "content", ...}}`.

### `build_identify_reports_prompt(all_metrics, existing_reports) -> str`
- **Parameters**: `all_metrics` - metric dicts; `existing_reports` - list of existing report names.
- **Use**: Constructs the LLM prompt asking it to review metrics and identify possible reports.

### `build_generate_report_prompt(report_name, metrics, required_metrics, analysis_summary) -> str`
- **Parameters**: `report_name` - target report; `metrics` - available metrics; `required_metrics` - needed metric keys; `analysis_summary` - dataset context.
- **Use**: Constructs the LLM prompt for generating a comprehensive report with structured sections.

### `_summarize_metrics(all_metrics) -> str`
- **Parameters**: `all_metrics` - list of metric dicts.
- **Use**: Builds a concise, categorized summary of available metrics for the LLM prompt. Groups metrics by category (Revenue, Sales, Profit, etc.) and shows sample values.

### `heuristic_identify_reports(all_metrics, existing_report_names) -> Dict`
- **Parameters**: `all_metrics` - metric dicts; `existing_report_names` - existing report names.
- **Use**: Fallback that matches metric names against keyword requirements for each known report type. No LLM required.

### `heuristic_generate_report(report_name, metrics, required_metrics, analysis_summary) -> Dict`
- **Parameters**: `report_name` - target report; `metrics` - available metrics; `required_metrics` - needed keys; `analysis_summary` - context.
- **Use**: Fallback that produces a basic template report listing available metrics. No LLM required.
