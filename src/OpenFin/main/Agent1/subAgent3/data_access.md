# data_access.py

## Key Objective
Loads filtered-data JSON files from `main/data/filtered-data/` (produced by subAgent1) and extracts metrics, analysis summaries, and metadata for subAgent3 research. Also handles saving research insight JSONs to `main/Agent1/insight-gens/`.

## Tools / Algorithms Used
- **JSON parsing**: Loads subAgent1's filtered output format (`source_file`, `processed_at`, `llm_analysis`, `computed_metrics`).
- **File I/O**: Scans directories, loads/saves JSON files.

## Key Objects

### `get_filtered_files() -> List[str]`
- **Parameters**: None.
- **Use**: Returns sorted list of JSON file paths in `main/data/filtered-data/`.

### `load_filtered_file(file_path: str) -> Optional[Dict]`
- **Parameters**: `file_path` - path to a filtered-data JSON file.
- **Use**: Loads a single filtered-data JSON file. Returns the full payload dict or None on failure.

### `extract_metrics(payload: Dict) -> Dict`
- **Parameters**: `payload` - full filtered-data JSON payload from subAgent1.
- **Use**: Extracts `computed_metrics` and flattens metadata (`_source_file`, `_processed_at`, `_analysis_summary`, `_col_*` mappings).

### `load_all_metrics() -> List[Dict]`
- **Parameters**: None.
- **Use**: Loads all filtered-data files and returns a list of metric dicts with metadata.

### `get_existing_insight_files() -> set`
- **Parameters**: None.
- **Use**: Returns a set of existing insight report filenames (without `.json` extension) in `main/Agent1/insight-gens/`. Used to avoid regenerating reports that already exist (per specs.md requirement).

### `topic_to_insight_filename(topic: str) -> str`
- **Parameters**: `topic` - research topic identifier (e.g., `"pricing_optimization_opportunities"`).
- **Use**: Converts a topic identifier to the expected insight filename (e.g., `"pricing_optimization_opportunities_research"`). Used to check if a report already exists for a topic.

### `save_insight(report_name: str, report_data: Dict) -> str`
- **Parameters**: `report_name` - name of the insight report; `report_data` - report content dict.
- **Use**: Saves a research insight report JSON to `main/Agent1/insight-gens/`. Returns the output path.
