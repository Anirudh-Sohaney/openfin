# research_analyzer.py

## Key Objective
Uses OpenRouter LLM to: (1) identify which of the 20 research topics are worth pursuing given current business metrics, and (2) generate professional research insight reports combining company metrics with web search findings. When LLM is unavailable, falls back to heuristic topic selection and template-based report generation.

## Tools / Algorithms Used
- **OpenRouter API (gpt-oss-120b:free)**: For intelligent topic prioritization and detailed report generation.
- **Metric summarization**: Extracts key metrics (revenue, profit, margins, top products, customer/supplier counts, ratios) into a concise LLM context.
- **No-opportunity detection**: Uses explicit `profitable_opportunity` boolean field from LLM response. Reports with `profitable_opportunity: false` are skipped (returns None).
- **Heuristic fallback (topic identification)**: `heuristic_identify_topics()` selects 12 default research topics from the specs list based on which metrics are present. Always includes core profit-improvement topics; adds supplier, market, and automation topics when relevant data exists.
- **JSON parsing with regex fallback**: Handles malformed LLM responses.
- **Heuristic fallback (report generation)**: `heuristic_generate_research_report()` produces a template-based 6-section report (Executive Summary, Current State, Market Research, Gap Analysis, Recommendations, Estimated Impact) without LLM, using available metric values.
- **In-code testing support**: Enables subAgent3 to function without API keys via heuristic fallbacks triggered on LLM failure.

## Configuration (Environment Variables)
- `OPENAI_API_KEY` - Required. OpenRouter API key.
- `OPENAI_BASE_URL` - Base URL (default: `https://openrouter.ai/api/v1`).
- `LLM_MODEL` - Model name (default: `openai/gpt-oss-120b:free`).

## Key Objects

### `ALL_RESEARCH_TOPICS: list[str]`
- **Use**: Master list of 20 research topic identifiers from specs.md.

### `identify_research_topics(metrics: Dict) -> Dict`
- **Parameters**: `metrics` - merged metrics dict.
- **Use**: Feeds metrics to LLM to prioritize research topics. Falls back to `heuristic_identify_topics()` on LLM failure. Returns `{prioritized_topics, product_categories, industry, skipped_topics}`.

### `heuristic_identify_topics(metrics: Dict) -> Dict`
- **Parameters**: `metrics` - merged metrics dict.
- **Use**: Fallback topic selection without LLM. Picks 12 default research topics (6 core + supplier + market + automation) based on available metric fields.

### `build_identify_topics_prompt(metrics: Dict) -> str`
- **Parameters**: `metrics` - merged metrics dict.
- **Use**: Constructs the LLM prompt with a summary of key metrics and the 20 available research topics.

### `generate_research_report(metrics, topic, search_results, product_categories, industry) -> Optional[Dict]`
- **Parameters**: `metrics` - current metrics; `topic` - topic identifier; `search_results` - Tavily results for this topic; `product_categories` - product context; `industry` - industry name.
- **Use**: Generates a single research insight report with sections: Executive Summary, Current State, Market Research, Gap Analysis, Recommendations, Estimated Impact. Returns None if no profitable opportunity found. Falls back to `heuristic_generate_research_report()` on LLM failure.

### `heuristic_generate_research_report(metrics, topic, product_categories, industry) -> Dict`
- **Parameters**: `metrics` - current metrics; `topic` - topic identifier; `product_categories` - product context; `industry` - industry name.
- **Use**: Fallback that generates a template-based 6-section report from available metrics without LLM.

### `build_research_report_prompt(metrics, topic, search_results, product_categories, industry) -> str`
- **Parameters**: Same as `generate_research_report`.
- **Use**: Constructs the LLM prompt for generating a single research insight report.

### `_summarize_metrics(metrics: Dict) -> str`
- **Parameters**: `metrics` - full metrics dict.
- **Use**: Extracts and formats key metrics (revenue, profit, margins, top/bottom products, customer/supplier counts, ratios) into a compact summary for LLM context.
