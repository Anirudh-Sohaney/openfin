# data_access.py

## Key Objective
Loads filtered-data JSON files from `main/data/filtered-data/` (produced by subAgent1) and extracts metrics, analysis summaries, and metadata for subAgent4's financial issue analysis. Also provides helpers for saving financial issue insight JSONs to `main/Agent1/insight-gens/` and checking for existing reports to avoid duplicates.

## Tools / Algorithms Used
- **JSON parsing**: Loads subAgent1's filtered output format (`source_file`, `processed_at`, `llm_analysis`, `computed_metrics`).
- **File I/O**: Scans directories, loads/saves JSON files.
- **Issue deduplication**: Converts issue IDs to expected insight filenames for checking existing reports.
- **Metrics extraction**: Flattens column mappings as `_col_*` metadata for LLM context.

## Key Objects

### `get_filtered_files() -> List[str]`
- **Parameters**: None.
- **Use**: Returns sorted list of JSON file paths in `main/data/filtered-data/`.

### `load_filtered_file(file_path: str) -> Optional[Dict]`
- **Parameters**: `file_path` - path to a filtered-data JSON file.
- **Use**: Loads a single filtered-data JSON file. Returns the full payload dict or None on failure.

### `extract_metrics(payload: Dict) -> Dict`
- **Parameters**: `payload` - full filtered-data JSON payload from subAgent1.
- **Use**: Extracts `computed_metrics` from the payload and adds metadata fields: `_source_file`, `_processed_at`, `_analysis_summary`, and `_col_*` column mappings.

### `load_all_metrics() -> List[Dict]`
- **Parameters**: None.
- **Use**: Loads all filtered-data files and returns a list of metric dicts with metadata. Main entry point for loading data for financial analysis.

### `get_existing_insight_files() -> set`
- **Parameters**: None.
- **Use**: Scans `main/Agent1/insight-gens/` for existing insight report JSON files. Returns a set of filenames (without .json extension). Used to avoid regenerating existing reports.

### `issue_to_insight_filename(issue_id: str) -> str`
- **Parameters**: `issue_id` - financial issue identifier (e.g., "declining_revenue").
- **Use**: Converts issue ID to expected insight filename (e.g., "declining_revenue_financial_issue_research"). Used for dedup checking.

### `save_insight(report_name: str, report_data: Dict) -> str`
- **Parameters**: `report_name` - display name of the report; `report_data` - report content dict.
- **Use**: Saves a generated financial issue insight JSON to `main/Agent1/insight-gens/`. Returns the output path.
