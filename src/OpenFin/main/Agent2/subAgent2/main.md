# main.py

## Key Objective
Orchestrate the response generation pipeline for subAgent 2: take the structured output from subAgent 1 and generate a professional financial advisory response using a single LLM call.

## Tools / Algorithms Used
- **response_generator**: For LLM-based response generation from the subAgent 1 result.
- **Activity log**: Timestamped logging to `log.txt` for Agent 2's active tracking. Uses write mode (overwrites each call) so only the current activity is shown.

## Key Objects

### `run(subagent1_result: Dict[str, Any]) -> Dict[str, Any]`
- **Parameters**: `subagent1_result` - The full result dict from subAgent 1, containing:
  - `prompt`: The user's original question
  - `analysis`: Analysis metadata (data_source, keywords, required_data_fields, summary)
  - `data`: Retrieved data (metrics, specific_fields, content, relevant_sections)
- **Use**: Main entry point. Calls `generate_response()` and wraps the result with source metadata. Handles errors gracefully (returns an apology message on failure).
- **Returns**: Dict with keys:
  - `prompt`: Original user prompt (echoed)
  - `response`: Dict with `answer` and `caveats` from the LLM
  - `source_info`: Dict with `data_source`, `source_type`, and `source` for attribution

### `_log(message: str)`
- **Parameters**: `message` - Log message string.
- **Use**: Writes a timestamped line to `log.txt` using write mode (overwrites each call), so only the current activity is persisted.

## Data Flow

```
subAgent 1 result dict
  │  { prompt, analysis, data }
  ▼
response_generator.generate_response()
  │  Builds context-aware prompt
  │  → 1 LLM call via OpenRouter
  │  → Parses JSON response
  ▼
Result dict returned
  │  { prompt, response: { answer, caveats }, source_info }
  ▼
Agent 2 delivers response to user
```
