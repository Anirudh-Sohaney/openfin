# subAgent2 — Directory Documentation

## Key Objective
Process the structured data identified and retrieved by subAgent 1 and generate a professional financial advisory response to the user's prompt. subAgent 2 is the final stage of Agent 2's pipeline: it takes the curated data and produces the answer the user sees.

## Data Sources Handled

| Source | Data Format | Response Style |
|--------|------------|----------------|
| `filtered-data` | Numerical metrics + specific field values | Data-driven answer with specific numbers |
| `base-reports` | PDF report sections (Executive Summary, Data, Analysis, Conclusion) | Narrative interpretation of report findings |
| `insights` | PDF insight sections (Current State, Market Research, Estimated Impact, etc.) | Advisory interpretation of research/issue reports |
| `internet` | Tavily web search results | Summary and synthesis of external research |
| `no_data_found` | Empty/fallback state | Transparent explanation of what data is missing |

## Key Initiating Function / Call Process

The main run function is `main.run(subagent1_result)`:

```
main.run(subagent1_result)
  │
  └─ [LLM Call] response_generator.generate_response()
       │
       ├─ build_response_prompt() — Constructs context-aware prompt
       │    ├─ Detects source_type (filtered_data, pdf_report, tavily, no_data_found)
       │    ├─ Formats data (metrics, specific_fields, relevant_sections, search results)
       │    ├─ Identifies missing fields (null values in specific_fields)
       │    └─ Injects transparency rules into the prompt
       │
       ├─ LLM Call via OpenRouter (gpt-oss-120b:free)
       │    └─ Returns JSON with "answer" and "caveats" keys
       │
       └─ Parses and validates response
```

The result is a structured dict containing:
- `response.answer`: The professional financial advisory response
- `response.caveats`: Data limitation notes (or empty)
- `source_info`: Attribution metadata (data_source, source_type, source)

## Uses Exactly 1 LLM Call

The single LLM call generates the complete response. The prompt dynamically adapts to include the right data for the source type. Missing data is pre-identified and injected as explicit warnings so the LLM can address limitations transparently.

## Tools / Algorithms Used
- **OpenRouter API (gpt-oss-120b:free)**: Single LLM call for response generation.
- **Dynamic prompt construction**: Adapts prompt structure based on source type (filtered-data, PDF reports, Tavily results, or no-data state).
- **Null field detection**: Identifies which `required_data_fields` returned null values and warns the LLM not to fabricate data for them.
- **Content truncation**: Caps metrics (30 items), sections (2000 chars), and search results (1500 chars) to stay within token budgets.
- **JSON parsing**: Extracts structured JSON from LLM output with code fence stripping and regex fallback.
- **Activity logging**: Timestamped log entries to `activity.log` for Agent 2's subAgent tracking.

## Major Files

| File | Purpose |
|------|---------|
| `response_generator.py` | [1 LLM Call] Builds context-aware prompt, calls LLM, parses response |
| `main.py` | Orchestrates: receive subAgent1 result → generate response → return structured result |

## Major Functions / Classes

| File | Object | Parameters | Use |
|------|--------|------------|-----|
| response_generator | `generate_response(subagent1_result)` | `subagent1_result: Dict` | [LLM Call] Generate financial advisor response from subAgent 1 output |
| response_generator | `build_response_prompt(subagent1_result)` | `subagent1_result: Dict` | Build context-aware LLM prompt based on data source type |
| response_generator | `_format_metrics(metrics, max_items)` | `metrics: Dict, max_items: int` | Format metrics for LLM prompt, marking nulls |
| response_generator | `_format_relevant_sections(sections)` | `sections: list` | Format report sections with headings |
| response_generator | `_format_tavily_results(results)` | `results: list` | Format Tavily search results |
| response_generator | `_get_llm_client()` | None | Configure OpenRouter client |
| response_generator | `_strip_json_fences(content)` | `content: str` | Remove markdown fences from LLM output |
| response_generator | `_parse_json_response(content)` | `content: str` | Parse JSON with regex fallback |
| main | `run(subagent1_result)` | `subagent1_result: Dict` | Main entry: generate → wrap → return |

## Error Handling

If the LLM call fails, `main.run()` catches the exception and returns a graceful fallback:
```json
{
    "prompt": "original prompt",
    "response": {
        "answer": "I apologize, but I encountered an error...",
        "caveats": "Error: <details>"
    },
    "source_info": {},
    "error": "exception details"
}
```
