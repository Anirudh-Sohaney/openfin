# main.py

## Key Objective
Orchestrates the full subAgent3 pipeline: loads filtered metrics, identifies research topics via LLM (with heuristic fallback), searches the internet via Tavily API, generates research insight reports, saves to `main/Agent1/insight-gens/`, and returns structured findings. Also provides in-code testing via `run_with_data()` with `_get_test_metrics()`.

## Tools / Algorithms Used
- **data_access**: For loading filtered JSON data produced by subAgent1 and saving insight reports.
- **tavily_search**: For internet research via Tavily Search API with advanced depth, AI-generated summaries, and 20 pre-defined query templates.
- **research_analyzer**: For LLM-based (OpenRouter) research topic prioritization and insight report generation, with heuristic fallbacks (`heuristic_identify_topics`, `heuristic_generate_research_report`).
- **File I/O & JSON**: For saving insights as structured JSON to Agent1/insight-gens/. Uses relative imports (`from .data_access import ...`).
- **Heuristic fallback**: When LLM is unavailable, `step_identify_topics` falls back to `heuristic_identify_topics()` and report generation falls back to `heuristic_generate_research_report()`.
- **In-code testing**: `_get_test_metrics()` provides 60+ realistic metrics. `run_with_data()` runs the full pipeline without file I/O.

## Key Objects

### `run(max_results_per_topic: int = 4, use_llm: bool = True) -> Dict`
- **Parameters**: `max_results_per_topic` - max Tavily results per topic (default 4); `use_llm` - if True use LLM + Tavily, if False heuristic-only.
- **Use**: Main production entry matching specs.md. Full 5-step pipeline: load metrics from files → identify topics → search → generate insights → collect results. When `use_llm=False`, skips all API calls entirely and uses heuristic fallbacks directly.

### `run_with_data(metrics, max_results_per_topic, skip_search) -> Dict`
- **Parameters**: `metrics: dict` - in-memory metrics; `max_results_per_topic: int` - results per topic; `skip_search: bool` - skip Tavily API.
- **Use**: Test entry point. Runs full pipeline with provided metrics dict, bypassing file I/O. Uses heuristics when LLM unavailable.

### `_get_test_metrics() -> Dict`
- **Parameters**: None.
- **Use**: Returns a 60+ key metrics dict with realistic financial data for in-code testing.

### `step_load_metrics() -> List[Dict]`
- **Parameters**: None.
- **Use**: Loads all filtered-data JSON files from `main/data/filtered-data/`, extracting metrics from subAgent1's output format.

### `step_identify_topics(merged_metrics) -> Dict`
- **Parameters**: `merged_metrics` - merged metric dict from all datasets.
- **Use**: Feeds metrics to LLM to prioritize research topics. Falls back to `heuristic_identify_topics()` (12 default topics) if LLM unavailable. Returns topic plan with product categories, industry, and prioritized/skipped topics.

### `step_search_internet(topic_plan, max_results_per_topic) -> Dict`
- **Parameters**: `topic_plan` - output from topic identification; `max_results_per_topic` - results per search.
- **Use**: Builds Tavily search queries from templates, searches each topic, returns results per topic.

### `step_generate_insights(topic_plan, merged_metrics, search_results) -> Dict`
- **Parameters**: `topic_plan` - research plan; `merged_metrics` - current metrics; `search_results` - Tavily results per topic.
- **Use**: Generates LLM research reports combining metrics + web search data. Skips topics where no profitable solution is found.

### `step_collect_results(insights) -> Dict`
- **Parameters**: `insights` - dict of report_title → report data.
- **Use**: Strips metadata and returns reports in spec format: `{"report title": {"subheading": "content", ...}}`.

### `_set_activity(status: str)`
- **Parameters**: `status` - activity string from specs ("researching online", "analyzing", "generating report", "idle", etc.).
- **Use**: Writes current activity to `log.txt` in overwrite mode (per specs: "current activity only, no past activity"). Also prints activity for debugging.
