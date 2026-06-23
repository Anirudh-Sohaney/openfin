# response_generator.py

## Key Objective
Single LLM call. Take the structured output from subAgent 1 (prompt, analysis metadata, and retrieved data) and generate a professional financial advisory response to the user's question.

## Tools / Algorithm Used
- **OpenRouter API (gpt-oss-120b:free)**: Sends the user's prompt and retrieved data to the LLM with a context-aware prompt that adapts to the data source type (filtered-data, base-reports, insights, internet, or no_data_found).
- **Dynamic prompt construction**: Builds an LLM prompt that includes formatted metrics, specific fields (with null handling for missing data), relevant report sections, or Tavily search results depending on the data source.
- **JSON parsing**: Extracts structured JSON from LLM output with code fence stripping and regex fallback.
- **Transparency enforcement**: The prompt explicitly identifies missing fields (null values) and instructs the LLM to disclose data limitations rather than fabricate numbers.

## Key Objects

### `generate_response(subagent1_result: Dict[str, Any]) -> Dict[str, str]`
- **Parameters**: `subagent1_result` - The full result dict from subAgent 1, containing `prompt`, `analysis`, and `data` keys.
- **Use**: [LLM Call] Builds a context-aware prompt and sends it to the LLM. Returns a dict with:
  - `answer`: The comprehensive, professional response to the user's question
  - `caveats`: Data limitation notes (missing fields, source limitations) or empty string

### `build_response_prompt(subagent1_result: Dict[str, Any]) -> str`
- **Parameters**: `subagent1_result` - The full result dict from subAgent 1.
- **Use**: Constructs the LLM prompt based on the data source type. Adapts the prompt's data section for:
  - `filtered_data` / `combined_filtered_data`: Formats metrics and specific fields
  - `pdf_report`: Formats relevant report sections with headings
  - `tavily`: Formats internet search results
  - `no_data_found`: Informs the LLM that no data was found
- **Missing field detection**: Identifies null values in `specific_fields` and injects a warning into the prompt.

### `_format_metrics(metrics: Dict, max_items: int = 30) -> str`
- **Parameters**: `metrics` - Dict of metric name → value; `max_items` - Token budget cap.
- **Use**: Formats metrics for LLM consumption. Truncates long strings. Marks null values as "NOT AVAILABLE". Caps at max_items to control token usage.

### `_format_relevant_sections(sections: list) -> str`
- **Parameters**: `sections` - List of dicts with `heading` and `content` keys.
- **Use**: Formats report/insight sections for LLM consumption. Truncates very long content to 2000 chars.

### `_format_tavily_results(results: list) -> str`
- **Parameters**: `results` - List of search result dicts with `title`, `url`, `content` keys.
- **Use**: Formats Tavily web search results for LLM consumption. Truncates content to 1500 chars per result.

### `_get_llm_client() -> OpenAI`
- **Parameters**: None.
- **Use**: Configures and returns an OpenAI client pointing to OpenRouter.

### `_strip_json_fences(content: str) -> str`
- **Parameters**: `content` - Raw LLM output.
- **Use**: Removes markdown code fences from the LLM response.

### `_parse_json_response(content: str) -> Dict`
- **Parameters**: `content` - Cleaned LLM output.
- **Use**: Parses JSON from LLM output with regex fallback for robustness.

## Response Format

The LLM returns a JSON object with exactly two keys:
```json
{
    "answer": "The comprehensive, well-structured response to the user's question.",
    "caveats": "Data limitations, missing fields, or sourcing notes (empty if none)."
}
```

## Data Source Handling

| Source Type | Prompt Section | Key Data Passed |
|-------------|---------------|-----------------|
| `filtered_data` | Specific fields + metrics | Numerical values, null markers for missing |
| `combined_filtered_data` | Specific fields + all merged metrics | Aggregated numerical values |
| `pdf_report` | Relevant sections | Section heading + content (truncated) |
| `tavily` | Search results | Title, URL, content per result |
| `no_data_found` | No-data message | Error/empty state |

## LLM Configuration
- **Model**: `os.environ.get("LLM_MODEL", "openai/gpt-oss-120b:free")`
- **Temperature**: 0.3 (balances professional narrative with factual accuracy)
- **Max Tokens**: 2500
