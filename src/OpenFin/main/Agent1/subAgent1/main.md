# main.py

## Key Objective
Orchestrates the full subAgent1 pipeline: detects files in `../../data/uploaded-data`, loads them, sends for LLM analysis, calculates financial metrics, saves results to `../../data/filtered-data`, and cleans up source files.

## Tools / Algorithms Used
- **data_loader**: For file format detection, loading, and standardization (handles CSV, TSV, XLSX, XLS, ODS).
- **llm_interface**: For LLM-based (OpenRouter) or heuristic column mapping and metric identification.
- **metrics_calculator**: For computing all derivable financial metrics with expense deduplication.
- **data_allocator**: For merging new metrics against existing filtered data with SNAPSHOT/TREND/LIST allocation rules.
- **File I/O & JSON**: For saving filtered results as structured JSON. Uses relative imports (`from .data_loader import ...`).

## Key Objects

### `run() -> Dict[str, Optional[str]]`
- **Parameters**: None.
- **Use**: The main run function matching specs.md. Scans `data/uploaded-data/` for all spreadsheet files and processes them sequentially through the pipeline. Returns a dict mapping filename to output path.

### `process_file(file_path: str) -> Optional[str]`
- **Parameters**: `file_path` - absolute path to a spreadsheet file.
- **Use**: Runs the full 5-step pipeline on a single file:
  1. Load and standardize via `data_loader.load_and_prepare()`
  2. Analyze via `llm_interface.analyze_dataframe()`
  3. Calculate metrics via `metrics_calculator.calculate_metrics()`
  4. Save results as JSON to `data/filtered-data/` via `data_allocator.allocate_and_merge()`
  5. Delete the source file from `data/uploaded-data/`

### `process_all() -> Dict[str, Optional[str]]`
- **Parameters**: None.
- **Use**: Calls `process_file()` on every file in the upload directory.

### `_set_activity(status: str)`
- **Parameters**: `status` - activity string ("breaking down data" or "idle").
- **Use**: Writes current activity to `log.txt` (overwrite mode, no history). Readable by Agent 1 for status tracking.

### `_save_results(original_filename, analysis, metrics) -> str`
- **Parameters**: `original_filename` - name of source file; `analysis` - LLM analysis dict; `metrics` - computed metrics dict.
- **Use**: Writes a JSON file containing the full analysis and computed metrics via data_allocator.

### `_delete_source(file_path: str)`
- **Parameters**: `file_path` - path to source file.
- **Use**: Removes the original file from the upload directory after successful processing.

### `test()`
- **Parameters**: None.
- **Use**: Runs the pipeline with inline test data (12-month DataFrame), bypassing file I/O. Prints all computed metrics. Invoked via `python3 -m main.Agent1.subAgent1.main --test`.
