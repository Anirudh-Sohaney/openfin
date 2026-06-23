# data_allocator.py

## Key Objective
Properly allocate new derived metrics against existing filtered data. When a new dataset arrives (e.g., revenue_2026.csv after revenue_2025.csv was already processed), this module intelligently merges the new metrics with old ones rather than creating a separate file.

## Tools / Algorithms Used
- **Regex filename normalization**: Strips dates, years, and suffixes to extract a base category name (e.g., "revenue_2025.csv" → "revenue").
- **Metric categorization**: Classifies each metric as SNAPSHOT, TREND, or LIST based on keyword patterns.
- **JSON merging**: Reads old filtered JSON, merges with new metrics according to category rules, writes back as a single combined file.
- **Period extraction**: Pulls a period ID from the filename or analysis for trend history keying.

## Key Objects

### `allocate_and_merge(new_source_filename, new_analysis, new_metrics, filtered_dir) -> Dict[str, Any]`
- **Parameters**: `new_source_filename: str` - name of new source file; `new_analysis: dict` - LLM analysis from new data; `new_metrics: dict` - computed metrics from new data; `filtered_dir: str` - path to filtered-data directory.
- **Use**: Main entry point. Detects existing filtered data for the same category, merges if found, returns the complete payload to save. Includes `is_merged`, `base_name`, `merged_from`, and `merge_period` metadata.

### `merge_metrics(old_metrics, new_metrics, period_id) -> Dict[str, Any]`
- **Parameters**: `old_metrics: dict` - existing computed metrics; `new_metrics: dict` - newly computed metrics; `period_id: str` - identifier for new period (e.g., "2026").
- **Use**: Applies allocation rules:
  - SNAPSHOT metrics (e.g., total_revenue, net_profit, customer_count) → replaced with new values
  - TREND metrics (e.g., revenue_growth, profit_volatility, marketing_roi) → stored in history dict keyed by period_id
  - LIST metrics (e.g., monthly_revenue_list) → appended

### `merge_analysis(old_analysis, new_analysis) -> Dict[str, Any]`
- **Parameters**: `old_analysis: dict` - existing LLM analysis; `new_analysis: dict` - new LLM analysis.
- **Use**: Merges analysis data — unions derivable_metrics and timeframes, concatenates summaries, uses new column_mappings.

### `categorize_metric(metric_name: str) -> str`
- **Parameters**: `metric_name: str` - name of the metric.
- **Use**: Returns "SNAPSHOT", "TREND", or "LIST" based on keyword patterns in the metric name.

### `_normalize_filename(filename: str) -> str`
- **Parameters**: `filename: str` - raw filename like "revenue_2025.csv".
- **Use**: Strips extensions, years, date prefixes, and numbers to extract base category (e.g., "revenue").

### `_find_existing_filtered(base_name: str, filtered_dir: str) -> Optional[str]`
- **Parameters**: `base_name: str` - normalized base name; `filtered_dir: str` - filtered data directory.
- **Use**: Finds an existing filtered JSON matching the base name, with fuzzy fallback.

### `get_output_filename(base_name: str) -> str`
- **Parameters**: `base_name: str` - normalized base name.
- **Use**: Returns standardized output filename: `{base_name}_filtered.json`.
