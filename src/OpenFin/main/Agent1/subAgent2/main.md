# main.py

## Key Objective
Orchestrates the full subAgent2 pipeline: loads filtered metrics from `main/data/filtered-data/`, uses LLM to identify which financial reports can be generated, filters out already-generated reports with unchanged metrics, generates each report via LLM, saves to `main/Agent1/base-gens/`, and returns organized report data.

## Tools / Algorithms Used
- **data_access**: For loading filtered JSON data produced by subAgent1. Parses the `computed_metrics` and `llm_analysis` payload format.
- **llm_interface**: For LLM-based (OpenRouter) report identification and generation, with heuristic fallbacks.
- **File I/O & JSON**: For saving reports as structured JSON. Uses relative imports (`from .data_access import ...`).
- **Metric change detection**: Compares `_metrics_used` snapshots from old reports against current metrics to decide whether regeneration is needed.

## Key Objects

### `run(force_regenerate: bool = False, use_llm: bool = True) -> Dict`
- **Parameters**: `force_regenerate` - regenerate all reports even if unchanged; `use_llm` - toggle LLM vs heuristic mode.
- **Use**: The main run function matching specs.md. Full 5-step pipeline: load metrics, identify possible reports, filter existing, generate, collect results.

### `step_load_metrics() -> List[Dict]`
- **Parameters**: None.
- **Use**: Loads all filtered-data JSON files from `main/data/filtered-data/`, extracting metrics from subAgent1's output format.

### `step_identify_reports(all_metrics, use_llm) -> List[Dict]`
- **Parameters**: `all_metrics` - list of metric dicts; `use_llm` - toggle LLM vs heuristic.
- **Use**: Prompts the LLM to determine which financial reports can be generated from available metrics. Falls back to heuristic pattern matching on failure.

### `step_filter_existing_reports(possible_reports, all_metrics) -> List[Dict]`
- **Parameters**: `possible_reports` - reports identified as possible; `all_metrics` - current metrics.
- **Use**: Filters out reports that already exist in `base-gens/` and have unchanged metrics. Merges metrics from all datasets.

### `step_generate_reports(reports_to_generate, all_metrics, use_llm) -> Dict`
- **Parameters**: `reports_to_generate` - filtered list of report info dicts; `all_metrics` - current metrics; `use_llm` - toggle LLM vs heuristic.
- **Use**: Iterates through reports and generates each one via LLM. Attaches `_metrics_used` metadata for future change detection.

### `step_collect_results(generated) -> Dict`
- **Parameters**: `generated` - dict of report_name to report data from generation step.
- **Use**: Strips `_metadata` fields and returns reports in the spec-compliant format: `{"Report name": {"Section header": "content", ...}}`.

### `generate_single_report(report_name, use_llm) -> Optional[Dict]`
- **Parameters**: `report_name` - name of a single report to generate; `use_llm` - toggle LLM vs heuristic.
- **Use**: Generate a single report on demand. Useful for testing or direct calls from Agent 1.

### `_set_activity(status: str)`
- **Parameters**: `status` - activity string ("thinking", "generating report for {name}", or "idle").
- **Use**: Writes current activity to `log.txt` (overwrite mode, no history). Readable by Agent 1 for status tracking.

### `test()`
- **Parameters**: None.
- **Use**: Runs the pipeline with inline mock metric data, bypassing file I/O. Prints identified reports and sample generated content. Invoked via `python3 -m main.Agent1.subAgent2.main --test`.
