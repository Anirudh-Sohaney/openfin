# subAgent3 — Directory Documentation

## Key Objective
Conducts online research to identify profit improvement opportunities. SubAgent3 runs in parallel with subAgents 2 and 4: it loads filtered metrics from `main/data/filtered-data/`, uses Tavily Search API to research the internet, and generates professional research insight reports with actionable recommendations.

## Key Initiating Function / Call Process

The main run functions are `main.run()` (production) and `main.run_with_data()` (testing):

```
main.run()  [production — reads from files]
  ├─ step_load_metrics()
  │    └─ data_access.load_all_metrics()
  │         └─ Load JSON from main/data/filtered-data/
  │
  ├─ step_identify_topics()
  │    └─ research_analyzer.identify_research_topics()
  │         ├─ LLM prompt (with heuristic fallback if LLM unavailable)
  │         └─ Falls back to heuristic_identify_topics()
  │
  ├─ step_search_internet()
  │    └─ tavily_search.search_topics()
  │         └─ Tavily API searches
  │
  ├─ step_generate_insights()
  │    └─ for each topic: generate_research_report()
  │         └─ LLM report (with heuristic fallback)
  │
  └─ step_collect_results() → save to insight-gens/

main.run_with_data(metrics, skip_search=True)  [testing — bypasses file I/O]
  ├─ Uses provided in-memory metrics dict directly
  ├─ step_identify_topics()
  │    └─ research_analyzer.identify_research_topics()
  │         ├─ LLM prompt (with heuristic fallback if LLM unavailable)
  │         └─ Falls back to heuristic_identify_topics()
  │
  ├─ step_search_internet()
  │    └─ tavily_search.search_topics()
  │         ├─ build_search_queries() — 20 templated queries
  │         └─ Tavily API searches (advanced depth, AI summaries)
  │
  ├─ step_generate_insights()
  │    └─ for each prioritized topic:
  │         research_analyzer.generate_research_report()
  │         ├─ LLM prompt: metrics + search results → 6-section report
  │         └─ Skip if no profitable solution found
  │
  └─ step_collect_results()
       └─ Return {"report title": {"subheading": "content", ...}}
```

## Tools / Algorithms Used

- **Tavily Search API**: Deep internet research with advanced search depth, AI-generated summaries, and structured content extraction. 20 pre-defined query templates covering supplier, pricing, market trends, customer, and operational topics.
- **OpenRouter API (gpt-oss-120b:free)**: Intelligent research topic prioritization and detailed insight report generation.
- **No-opportunity detection**: LLM returns explicit `profitable_opportunity` boolean; reports with `false` are skipped (returns None).
- **Heuristic fallback**: `heuristic_identify_topics()` provides default research topics (12 topics from specs) when LLM is unavailable. `heuristic_generate_research_report()` generates template-based reports without LLM. Both ensure the subAgent operates correctly even without API keys.
- **JSON parsing with regex fallback**: Handles malformed LLM responses.
- **In-code testing**: `_get_test_metrics()` returns 60+ realistic metrics for testing without file I/O. `run_with_data()` accepts in-memory metrics and runs the full pipeline with heuristic fallbacks.

## Major Files

| File | Purpose |
|------|---------|
| `data_access.py` | Loads filtered-data JSON from subAgent1; saves insight JSONs to Agent1/insight-gens/ |
| `tavily_search.py` | Tavily Search API wrapper with 20 templated research queries and result formatting |
| `research_analyzer.py` | OpenRouter LLM for topic prioritization and 6-section research report generation |
| `main.py` | Orchestrates the full pipeline: load → identify → search → generate → save → return |

## Major Functions / Classes

| File | Object | Parameters | Use |
|------|--------|------------|-----|
| data_access | `load_all_metrics()` | None | Load all filtered metrics from filtered-data/ |
| data_access | `get_existing_insight_files()` | None | Return set of existing insight filenames from Agent1/insight-gens/ (dedup) |
| data_access | `topic_to_insight_filename(topic)` | `topic: str` | Map topic ID to expected insight filename |
| data_access | `save_insight(name, data)` | `name: str, data: dict` | Save research insight JSON to Agent1/insight-gens/ |
| tavily_search | `build_search_queries(topics, cats, industry, year, topic_contexts)` | `topics: list, cats: str, industry: str, year: str, topic_contexts: dict` | Build templated search queries with LLM context |
| tavily_search | `search_topic(query, max_results)` | `query: str, max_results: int` | Single Tavily advanced search |
| tavily_search | `search_topics(queries, max_results_per_topic)` | `queries: dict, max_results_per_topic: int` | Multi-topic Tavily search |

| research_analyzer | `identify_research_topics(metrics)` | `metrics: dict` | LLM prioritizes 20 research topics; falls back to heuristic |
| research_analyzer | `heuristic_identify_topics(metrics)` | `metrics: dict` | Fallback: selects 12 default research topics from metric presence |
| research_analyzer | `generate_research_report(metrics, topic, results, cats, industry)` | `metrics: dict, topic: str, results: dict, cats: str, industry: str` | Generate 6-section insight report; falls back to heuristic |
| research_analyzer | `heuristic_generate_research_report(metrics, topic, cats, industry)` | `metrics: dict, topic: str, cats: str, industry: str` | Fallback: template-based report without LLM |
| research_analyzer | `build_identify_topics_prompt(metrics)` | `metrics: dict` | Build topic identification prompt |
| research_analyzer | `build_research_report_prompt(...)` | Same as generate | Build report generation prompt |
| main | `run(max_results_per_topic, use_llm)` | `max_results_per_topic: int, use_llm: bool` | Main production entry: full pipeline; when `use_llm=False` skips all API calls and goes straight to heuristics |
| main | `run_with_data(metrics, max_results_per_topic, skip_search)` | `metrics: dict, max_results_per_topic: int, skip_search: bool` | Test entry: full pipeline with in-memory data, heuristic-only safe |
| main | `_get_test_metrics()` | None | Return 60+ realistic test metrics for in-code testing |
| main | `_set_activity(status)` | `status: str` | Write current activity to log.txt (overwrite mode, specs-compliant) |

## Data Flow

```
subAgent1 output: main/data/filtered-data/*.json
  │  (computed_metrics + llm_analysis)
  ▼
data_access.load_all_metrics()
  │  → List of metric dicts with metadata
  ▼
research_analyzer.identify_research_topics()
  │  → { prioritized_topics, product_categories, industry, skipped_topics }
  ▼
tavily_search.search_topics()
  │  → Tavily API (advanced depth, AI summaries)
  │  → { topic: { answer, results: [...] } }
  ▼
research_analyzer.generate_research_report() [for each topic]
  │  → 6-section report: Executive Summary, Current State, Market Research,
  │    Gap Analysis, Recommendations, Estimated Impact
  │  → Skip if no profitable solution found
  ▼
data_access.save_insight()
  │  → Saved to main/Agent1/insight-gens/*.json
  ▼
Returned to Agent 1 as:
  { "Report Title": { "Subheading": "content", ... } }
```

## Research Topics (20 from specs.md)

Supplier-focused: alternative_suppliers, lower_supplier_pricing, better_supplier_terms, supplier_dependency_risks
Market-focused: emerging_high_demand_products, declining_product_categories, seasonal_market_trends, competitor_pricing_trends
Financial benchmarking: industry_profit_margin_benchmarks, industry_expense_benchmarks
Operations: inventory_optimization_opportunities, pricing_optimization_opportunities
Growth: customer_retention_opportunities, revenue_diversification_opportunities, new_sales_channel_opportunities, geographic_expansion_opportunities
Efficiency: cost_reduction_opportunities, automation_opportunities, operational_efficiency_improvements, cash_flow_optimization_strategies
