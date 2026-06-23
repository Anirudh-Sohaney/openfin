# main.py

## Key Objective
Orchestrates the full subAgent4 pipeline: loads filtered metrics from `main/data/filtered-data/`, uses LLM + heuristic analysis to identify financial issues and inefficiencies, filters out issues that already have existing insight reports, generates professional diagnostic reports for each issue, saves them to `main/Agent1/insight-gens/`, and returns organized financial issue insight data. Also provides in-code testing via `run_with_data()` with `_get_test_metrics()`.

## Tools / Algorithms Used
- **data_access**: For loading filtered JSON data produced by subAgent1 and saving insight reports.
- **financial_analyzer**: For LLM-based (OpenRouter) issue identification and report generation, with heuristic fallback and LLM+heuristic merging.
- **File I/O & JSON**: For saving reports as structured JSON. Uses relative imports (`from .data_access import ...`).
- **LLM + Heuristic merging**: Both LLM and heuristic analyses run and results are merged for comprehensive issue coverage.
- **In-code testing**: `_get_test_metrics()` provides 60+ intentionally stressed metrics. `run_with_data()` runs the full pipeline without file I/O using heuristic-only analysis.

## Key Objects

### `run(use_llm: bool = True) -> Dict`
- **Parameters**: `use_llm` - if True, use LLM + heuristic merging; if False, heuristic only.
- **Use**: Main production entry matching specs.md. Full 6-step pipeline: load metrics → identify issues → filter existing → generate reports → collect results → return.

### `run_with_data(metrics, use_llm) -> Dict`
- **Parameters**: `metrics: dict` - in-memory metrics; `use_llm: bool` - toggle LLM vs heuristic.
- **Use**: Test entry point. Runs full pipeline with provided metrics dict, bypassing file I/O. Uses heuristic-only when `use_llm=False`.

### `_get_test_metrics() -> Dict`
- **Parameters**: None.
- **Use**: Returns a 60+ key metrics dict with intentionally stressed values (negative cash flow, low reserves, high debt ratio, etc.) designed to trigger financial issue detection for testing.

### `step_load_metrics() -> List[Dict]`
- **Parameters**: None.
- **Use**: Loads all filtered-data JSON files from `main/data/filtered-data/`, extracting metrics from subAgent1's output format.

### `_merge_issue_plans(primary_plan, secondary_plan) -> Dict`
- **Parameters**: `primary_plan` - primary issue plan dict; `secondary_plan` - secondary issue plan dict.
- **Use**: Merges two issue plans without duplicates. Primary plan takes precedence for overlapping issue_ids. Used to combine LLM and heuristic findings.

### `step_identify_issues(merged_metrics, use_llm) -> Dict`
- **Parameters**: `merged_metrics` - merged metrics dict; `use_llm` - toggle LLM+heuristic vs heuristic only.
- **Use**: Runs LLM analysis and heuristic analysis in parallel, then merges results. Ensures comprehensive financial issue coverage.

### `step_filter_existing_reports(issue_plan) -> Dict`
- **Parameters**: `issue_plan` - dict with identified_issues list.
- **Use**: Filters out issues that already have insight reports in `Agent1/insight-gens/`. Avoids overwriting existing reports.

### `step_generate_issue_reports(issue_plan, merged_metrics, use_llm) -> Dict`
- **Parameters**: `issue_plan` - filtered issue plan; `merged_metrics` - current metrics; `use_llm` - toggle LLM vs heuristic.
- **Use**: Iterates through identified issues and generates a professional 6-section diagnostic report for each via LLM (or heuristic fallback). Attaches metadata and saves to disk.

### `step_collect_results(insights) -> Dict`
- **Parameters**: `insights` - dict of report_title → report data.
- **Use**: Strips `_metadata` fields and returns reports in the spec-compliant format: `{"Report Title": {"Section Header": "content", ...}}`.

### `_set_activity(status: str)`
- **Parameters**: `status` - activity string from specs ("assessing issues" or "idle").
- **Use**: Writes current activity to `log.txt` in overwrite mode (per specs: "current activity only, no past activity"). Also prints activity for debugging.
