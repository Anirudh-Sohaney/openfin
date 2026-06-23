# tavily_search.py

## Key Objective
Interfaces with the Tavily Search API for deep internet research — supplier alternatives, market trends, competitor pricing, industry benchmarks, and profit improvement opportunities. Uses the official `tavily-python` SDK.

## Tools / Algorithms Used
- **Tavily Search API (Python SDK)**: Performs advanced-depth web searches returning AI-generated summaries and extracted page content.
- **Pre-defined query templates**: 20 research topic query templates keyed to the topic identifiers from specs.md. Templates automatically format product categories, industry, year, and LLM-identified context into search queries.

## Configuration (Environment Variables)
- `TAVILY_API_KEY` - Required. Tavily API key.

## Key Objects

### `RESEARCH_QUERY_TEMPLATES: dict[str, str]`
- **Use**: Mapping of 20 research topic identifiers to templated search query strings. Templates use `{product_categories}`, `{industry}`, and `{current_year}` placeholders.

### `build_search_queries(research_topics, product_categories, industry, current_year, topic_contexts) -> Dict[str, str]`
- **Parameters**: `research_topics` - list of topic identifiers; `product_categories` - product context; `industry` - industry name; `current_year` - year string; `topic_contexts` - optional dict mapping topic→context_for_search from LLM.
- **Use**: Formats the query templates with business context to produce ready-to-execute search queries. Appends LLM-identified context strings to make searches more specific.

### `search_topic(query: str, max_results: int = 5) -> Optional[Dict]`
- **Parameters**: `query` - search query string; `max_results` - max results.
- **Use**: Performs a single advanced-depth Tavily search. Returns `{query, answer, results}` or None on failure.

### `search_topics(queries: Dict, max_results_per_topic: int = 5) -> Dict`
- **Parameters**: `queries` - topic→query mapping; `max_results_per_topic` - results per search.
- **Use**: Runs Tavily searches sequentially for multiple topics. Returns topic→result dict.


