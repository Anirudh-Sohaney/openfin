# main.py

## Key Objective
Orchestrate the single-LLM-call pipeline for subAgent 1:
1. Analyze user prompt (1 LLM call to identify data requirements)
2. Retrieve data from local files (JSON metrics or PDF reports) or internet
3. Return structured result for subAgent 2 consumption

## Tools / Algorithms Used
- **prompt_analyzer**: For LLM-based analysis of user prompt to determine data source, keywords, and required fields.
- **data_retriever**: For fetching data from filtered-data JSONs, base-reports PDFs, insights PDFs, or Tavily, with specific field extraction.
- **Activity log**: Timestamped logging to `log.txt` for Agent 2's active tracking. Uses write mode (overwrites each call) so only the current activity is shown.

## Key Objects

### `run(user_prompt: str) -> Dict[str, Any]`
- **Parameters**: `user_prompt` - Natural-language question from the user.
- **Use**: Main run function. Executes the pipeline:
  1. `analyze_prompt()` — LLM identifies data requirements (1 call)
  2. `retrieve_data()` — Fetch data from the identified source, with PDF text extraction or JSON field extraction as appropriate
- **Returns**: Dict with keys: prompt, analysis, data

### `_log(message: str)`
- **Parameters**: `message` - Log message string.
- **Use**: Writes a timestamped line to `log.txt` using write mode (overwrites each call), so only the current activity is persisted.

## Data Sources Handled

| Source | Format | Loaded By |
|--------|--------|-----------|
| filtered-data | JSON | `data_retriever._load_filtered_data()` |
| base-reports | PDF | `data_retriever._load_base_reports()` (with JSON fallback) |
| insights | PDF | `data_retriever._load_insights()` (with JSON fallback) |
| internet | Tavily API | `data_retriever._search_internet()` |
