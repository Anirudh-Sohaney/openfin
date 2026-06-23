# data_access.py

## Key Objective
Loads filtered-data JSON files from `main/data/filtered-data/` (produced by subAgent1) and extracts metrics, analysis summaries, and metadata. Also handles saving and comparing generated reports in `main/Agent1/base-gens/`.

## Tools / Algorithms Used
- **JSON parsing**: Loads subAgent1's filtered output format (`source_file`, `processed_at`, `llm_analysis`, `computed_metrics`).
- **File I/O**: Scans directories, loads/saves JSON files.
- **Metric change detection**: Compares old `_metrics_used` snapshots against current metric values using relative difference thresholds (1%) to determine if a report should be regenerated.
- **Safe arithmetic**: Guards against division by zero and type mismatches during metric comparison.

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
- **Use**: Loads all filtered-data files and returns a list of metric dicts with metadata. This is the main entry point for loading data.

### `get_existing_reports() -> Dict[str, str]`
- **Parameters**: None.
- **Use**: Scans `main/Agent1/base-gens/` for already generated report JSON files. Returns mapping of report name to file path.

### `load_existing_report(report_name: str) -> Optional[Dict]`
- **Parameters**: `report_name` - name of an existing report.
- **Use**: Loads a previously generated report for comparison purposes (checking if metrics changed).

### `save_report(report_name: str, report_data: Dict) -> str`
- **Parameters**: `report_name` - name of the report; `report_data` - report content dict.
- **Use**: Saves a generated report JSON to `main/Agent1/base-gens/`. Returns the output path.

### `compare_metrics_for_report(report_name, current_metrics, old_report) -> bool`
- **Parameters**: `report_name` - report name; `current_metrics` - current metric values; `old_report` - previously saved report dict.
- **Use**: Compares `_metrics_used` from an old report against current metrics. Returns True if values differ by more than 1% (or types changed), indicating the report should be regenerated.
