# financial_analyzer.py

## Key Objective
Uses LLM (via OpenRouter) and heuristic analysis to:
1. Analyze financial metrics and identify critical financial issues and inefficiencies from a list of 60+ known issues
2. Generate professional financial issue reports with data-backed findings, root cause analysis, and actionable recommendations

Both LLM and heuristic approaches run and results are merged for comprehensive coverage.

## Tools / Algorithms Used
- **OpenRouter API**: Free model `openai/gpt-oss-120b:free` (configurable via `LLM_MODEL` env var) for intelligent issue identification and detailed report generation. Uses `HTTP-Referer` and `X-Title` headers for OpenRouter ranking.
- **Heuristic threshold analysis**: Complementary fallback using hardcoded metric thresholds (revenue concentration > 15%, expense ratio > 80%, revenue per employee < $1000, etc.) covering 30+ issue categories.
- **LLM + Heuristic merging**: LLM findings take precedence; heuristic fills in gaps for comprehensive coverage.
- **Bold issue identification prompt**: LLM is instructed to be aggressive in finding issues and to make reasonable inferences from available data.
- **Metrics summarization**: Comprehensive structured summary of ALL available metrics organized by category with data coverage notes.
- **JSON parsing with regex fallback**: Handles malformed LLM responses gracefully.
- **Narrowed exception handling**: API errors and JSON parsing errors handled separately.

## Configuration (Environment Variables)
- `OPENAI_API_KEY` - Required. OpenRouter API key.
- `OPENAI_BASE_URL` - Base URL (default: `https://openrouter.ai/api/v1`).
- `LLM_MODEL` - Model name (default: `openai/gpt-oss-120b:free`). Also supports `openrouter/owl-alpha`.

## Key Objects

### `ALL_FINANCIAL_ISSUES: list[str]`
- **Use**: Master list of 67 known financial issues from specs.md. Sent to the LLM as the universe of possible issues to evaluate.

### `identify_financial_issues(metrics) -> Dict`
- **Parameters**: `metrics` - merged metrics dict from filtered data.
- **Use**: Builds LLM prompt for issue identification, calls OpenRouter, parses JSON response. Falls back to heuristic analysis if LLM returns 0 issues or fails.

### `generate_issue_report(metrics, issue_id, severity, rationale, context, key_metrics) -> Optional[Dict]`
- **Parameters**: `metrics` - full metrics dict; `issue_id` - issue identifier; `severity` - severity level; `rationale` - why issue was flagged; `context` - report context; `key_metrics` - relevant metric keys.
- **Use**: Generates a 6-section diagnostic report via LLM. Falls back to heuristic report generation on API/parse failure.

### `build_identify_issues_prompt(metrics) -> str`
- **Parameters**: `metrics` - available metrics dict.
- **Use**: Constructs the LLM prompt for issue identification. Shows all available metrics, what can be analyzed, and explicitly encourages bold inference.

### `build_issue_report_prompt(metrics, issue_id, severity, rationale, context, key_metrics) -> str`
- **Parameters**: Same as `generate_issue_report`.
- **Use**: Constructs the LLM prompt for generating a detailed diagnostic report with 6 required sections.

### `_summarize_metrics_for_issues(metrics) -> str`
- **Parameters**: `metrics` - dict of all available metrics.
- **Use**: Builds a comprehensive, categorized summary of ALL available metrics. Shows raw dump, detailed breakdown by category, and a data coverage note.

### `heuristic_identify_issues(metrics) -> Dict`
- **Parameters**: `metrics` - merged metrics dict.
- **Use**: Fallback that identifies issues using hardcoded metric thresholds. Detects revenue concentration, profit concentration, underperforming products, inefficient product mix, employee productivity issues, and more. Includes dedup with severity merging.

### `heuristic_generate_issue_report(metrics, issue_id, severity, rationale, context, key_metrics) -> Dict`
- **Parameters**: Same as `generate_issue_report`.
- **Use**: Fallback that produces a basic template report listing available metrics with simple analysis. Used when the LLM is unavailable.

### `_get_llm_client() -> OpenAI`
- **Parameters**: None.
- **Use**: Configures and returns an OpenAI client pointed at the OpenRouter API with appropriate headers.

### `_strip_json_fences(content: str) -> str`
- **Parameters**: `content` - raw LLM response text.
- **Use**: Removes markdown code fences (```json ... ```) from LLM responses.

### `_parse_json_response(content: str) -> Dict`
- **Parameters**: `content` - cleaned LLM response text.
- **Use**: Parses LLM response as JSON with regex fallback extraction for malformed responses.
