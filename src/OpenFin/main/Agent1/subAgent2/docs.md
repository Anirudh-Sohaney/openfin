# subAgent2 — Directory Documentation

## Key Objective
Develops basic financial reports from the metrics computed by subAgent1. SubAgent2 is the second step in Agent 1's pipeline: it reads filtered data from `main/data/filtered-data/`, identifies which reports can be generated, and produces professional financial reports with Data, Analysis, and Conclusion sections.

## Key Initiating Function / Call Process

The main run function is `main.run()`:

```
main.run()
  ├─ step_load_metrics()
  │    └─ data_access.load_all_metrics()
  │         └─ for each JSON file in main/data/filtered-data/:
  │              load_filtered_file() → extract_metrics()
  │
  ├─ step_identify_reports()
  │    └─ llm_interface.identify_possible_reports()
  │         └─ LLM prompt: "Given these metrics, what reports can be generated?"
  │
  ├─ step_filter_existing_reports()
  │    └─ data_access.compare_metrics_for_report()
  │         └─ Check if existing report's metrics have changed
  │
  ├─ step_generate_reports()
  │    └─ for each report to generate:
  │         llm_interface.generate_report()
  │         └─ LLM prompt: "Generate a comprehensive [Report Name]"
  │         data_access.save_report()
  │         └─ Save to main/Agent1/base-gens/
  │
  └─ step_collect_results()
       └─ Return {"Report name": {"Section header": "content", ...}}
```

## Tools / Algorithms Used

- **OpenRouter API (gpt-oss-120b:free)**: Intelligent report identification and detailed narrative generation via free LLM models.
- **Heuristic pattern matching**: Fallback report identification and template generation without LLM.
- **Metric categorization**: Groups 80+ metrics into categories (Revenue, Sales, Profit, Expense, Inventory, etc.) for structured LLM prompts.
- **Metric change detection**: Compares `_metrics_used` snapshots from old reports against current metric values to avoid redundant regeneration.
- **JSON parsing with regex fallback**: Handles malformed LLM responses gracefully.
- **Safe file I/O**: Directory auto-creation, encoding-safe JSON serialization.

## Major Files

| File | Purpose |
|------|---------|
| `data_access.py` | Loads filtered-data JSON from subAgent1; saves/compares reports in base-gens/ |
| `llm_interface.py` | Interfaces with OpenRouter LLM to identify possible reports and generate detailed narratives |
| `main.py` | Orchestrates the full pipeline: load → identify → filter → generate → save → return |

## Major Functions / Classes

| File | Object | Parameters | Use |
|------|--------|------------|-----|
| data_access | `load_all_metrics()` | None | Load and extract all metrics from filtered-data/ |
| data_access | `extract_metrics(payload)` | `payload: dict` | Extract computed_metrics + metadata from subAgent1 output |
| data_access | `save_report(report_name, data)` | `report_name: str, data: dict` | Save generated report to base-gens/ |
| data_access | `compare_metrics_for_report(name, current, old)` | `name: str, current: dict, old: dict` | Check if metrics changed (1% threshold) |
| llm_interface | `identify_possible_reports(metrics, existing)` | `metrics: list, existing: list` | LLM identifies which reports can be generated |
| llm_interface | `generate_report(name, metrics, required, summary)` | `name: str, metrics: dict, required: list, summary: str` | LLM generates a detailed report |
| llm_interface | `_summarize_metrics(metrics)` | `metrics: list` | Categorize and summarize metrics for LLM prompt |
| llm_interface | `heuristic_identify_reports(metrics, existing)` | `metrics: list, existing: list` | Pattern-match fallback for report ID |
| llm_interface | `heuristic_generate_report(name, metrics, required, summary)` | `name: str, metrics: dict, required: list, summary: str` | Template fallback for report generation |
| main | `run(force_regenerate, use_llm)` | `force_regenerate: bool, use_llm: bool` | Main entry: full pipeline |
| main | `generate_single_report(name, use_llm)` | `name: str, use_llm: bool` | Generate one report on demand |
| main | `_set_activity(status)` | `status: str` | Write current activity to log.txt (overwrite) |
| main | `test()` | None | Run pipeline with inline mock data, print results |

## Data Flow

```
subAgent1 output: main/data/filtered-data/*.json
  │  (computed_metrics + llm_analysis)
  ▼
data_access.load_all_metrics()
  │  → List of metric dicts with metadata
  ▼
llm_interface.identify_possible_reports()
  │  → { possible_reports: [...], unavailable_reports: [...] }
  ▼
data_access.compare_metrics_for_report() [filter existing]
  │  → Filtered list of reports to generate
  ▼
llm_interface.generate_report() [for each report]
  │  → { "Report Name": { "Section": "content", ... } }
  ▼
data_access.save_report()
  │  → Saved to main/Agent1/base-gens/*.json
  ▼
Returned to Agent 1 as:
  { "Report Name": { "Section Header": "section content", ... } }
```

## Report Format (per specs.md)

Each generated report follows this structure:
```json
{
  "Revenue Report": {
    "Data": "The company reported total revenue of $X...",
    "Analysis": "Revenue has shown a X% growth trend...",
    "Conclusion": "Based on the analysis, the company should..."
  }
}
```

Core sections always required: **Data**, **Analysis**, **Conclusion**. Additional sections (Executive Summary, Methodology, Risk Assessment, Recommendations, Comparison) are included when appropriate to the report type.
