# prompt_analyzer.py

## Key Objective
Single LLM call. Analyze a user's prompt to determine what data is needed to answer it — the data source, relevant keywords, and specific metric/field names to extract.

## Tools / Algorithm Used
- **OpenRouter API (gpt-oss-120b:free)**: Sends user prompt to LLM with a structured description of available data sources including:
  - filtered-data JSON (structured metrics)
  - base-reports PDF (narrative financial reports with Executive Summary, Analysis, Conclusions)
  - insights PDF (research-driven analysis with pricing, cost, market, and risk insights)
  - internet/Tavily (live web search)
- **JSON parsing**: Extracts structured JSON from LLM output with code fence stripping and regex fallback.

## Key Objects

### `analyze_prompt(user_prompt: str) -> Dict`
- **Parameters**: `user_prompt` - The user's question.
- **Use**: [LLM Call] Sends prompt to LLM and returns:
  - `data_source`: One of "filtered-data", "base-reports", "insights", "internet"
  - `data_keywords`: Financial concepts mentioned (e.g., ["revenue", "products"])
  - `required_data_fields`: Specific metric/field names needed. If calculation is required (projection, growth rate, etc.), lists the data fields needed as inputs to that calculation.
  - `tavily_query`: Search query string if source is internet, else null
  - `summary`: Brief explanation of what the user is asking

### `build_analysis_prompt(user_prompt: str) -> str`
- **Parameters**: `user_prompt` - The user's question.
- **Use**: Builds the LLM prompt describing available data sources, known field names, and routing rules. Notes that base-reports and insights are PDF-based (text extracted).

### `_get_llm_client() -> OpenAI`
- **Parameters**: None.
- **Use**: Configures and returns an OpenAI client pointing to OpenRouter.
