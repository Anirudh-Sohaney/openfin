# subAgent1 — Directory Documentation

## Key Objective
Process uploaded spreadsheet data into analysis-ready financial metrics. SubAgent1 is the first step in Agent 1's pipeline: it breaks down raw data into ~80+ standardized financial metrics that downstream subAgents (2, 3, 4) consume.

## Key Initiating Function / Call Process

The main run function is `main.run()`:

```
main.run()
  └─ process_all()
       └─ for each file in main/data/uploaded-data/:
            process_file(file_path)
              ├─ data_loader.load_and_prepare()       # Step 1: Load & standardize
              ├─ llm_interface.analyze_dataframe()    # Step 2: LLM analysis
              ├─ metrics_calculator.calculate_metrics()  # Step 3: Compute metrics
              ├─ _save_results()                      # Step 4: Save to filtered-data/
              └─ _delete_source()                     # Step 5: Remove from uploaded-data/
```

## Tools / Algorithms Used

- **pandas**: Core data manipulation, type coercion, time-series resampling, and aggregation.
- **OpenRouter API (gpt-oss-120b:free)**: Intelligent column mapping and metric selection via free LLM models.
- **Heuristic pattern matching**: Fallback column identification without LLM.
- **Column mapping validation**: Post-processing safety checks that detect and correct common LLM column-mapping errors (e.g., confusing monetary sales columns with unit/quantity columns).
- **HHI (Herfindahl-Hirschman Index)**: Concentration scoring for customers, suppliers, revenue, and profit.
- **Simple linear projection**: Forecasting via average period-over-period change extrapolation.
- **Safe arithmetic**: All division operations guard against zero/None/NaN values.

## Major Files

| File | Purpose |
|------|---------|
| `data_loader.py` | Accepts all spreadsheet formats (CSV, XLSX, XLS, ODS, TSV), standardizes, detects date columns |
| `llm_interface.py` | Interfaces with OpenRouter LLM (free models) to analyze data variables and identify derivable metrics |
| `data_allocator.py` | Properly allocates new metrics against existing filtered data — snapshot metrics replaced, trend metrics preserved as history, list metrics appended |
| `metrics_calculator.py` | Computes ~80+ financial metrics from the DataFrame |
| `main.py` | Orchestrates the full pipeline: load → analyze → calculate → allocate → save → cleanup |

## Major Functions / Classes

| File | Object | Parameters | Use |
|------|--------|------------|-----|
| data_loader | `load_and_prepare(file_path)` | `file_path: str` | Load and standardize a spreadsheet, detect date column |
| data_loader | `standardize_dataframe(df)` | `df: pd.DataFrame` | Clean columns, strip currency symbols, extract numbers from mixed text, convert to numeric, parse dates |
| llm_interface | `analyze_dataframe(df, date_col)` | `df: DataFrame, date_col: str|None` | Send to LLM for analysis, fall back to heuristics |
| llm_interface | `heuristic_analysis(df, date_col)` | `df: DataFrame, date_col: str|None` | Pattern-match column names without LLM |
| llm_interface | `_validate_mappings(mappings)` | `mappings: dict` | Post-process column mappings to fix common LLM mistakes (sales vs quantity column confusion) |
| llm_interface | `build_analysis_prompt(data_description)` | `data_description: dict` | Build LLM prompt with CRITICAL DISTINCTION clarifying monetary sales vs unit quantity columns |
| data_allocator | `allocate_and_merge(filename, analysis, metrics, dir)` | `filename: str, analysis: dict, metrics: dict, dir: str` | Main entry: detect existing filtered data, merge snapshot/trend/list metrics, return combined payload |
| data_allocator | `merge_metrics(old, new, period_id)` | `old: dict, new: dict, period_id: str` | Apply SNAPSHOT (replace), TREND (history dict), LIST (append) allocation rules |
| data_allocator | `categorize_metric(name)` | `name: str` | Classify metric as SNAPSHOT, TREND, or LIST |
| metrics_calculator | `MetricsCalculator` (class) | `df, date_col, mappings, derivable_metrics, timeframes` | Compute all derivable financial metrics |
| metrics_calculator | `calculate_metrics(...)` | Same as MetricsCalculator | Convenience wrapper function |
| main | `run()` | None | Main entry point: process all files in uploaded-data |
| main | `process_file(file_path)` | `file_path: str` | Full pipeline on a single file (includes data allocation step) |
| main | `_set_activity(status)` | `status: str` | Write current activity ("breaking down data" or "idle") to log.txt (overwrite) |
| main | `test()` | None | Run pipeline with inline test data, print results |
| llm_interface | `_make_json_safe(obj)` | `obj: any` | Recursively convert Timestamps etc. to JSON-safe strings |

## Data Flow

```
Uploaded spreadsheet (CSV/XLSX/ODS/etc.)
  │
  ▼
data_loader.load_and_prepare()
  │  → pandas DataFrame (standardized, with date column ID'd)
  ▼
llm_interface.analyze_dataframe()
  │  → { column_mappings, derivable_metrics, timeframes, analysis_summary }
  ▼
metrics_calculator.calculate_metrics()
  │  → { metric_name: value, ... }
  ▼
data_allocator.allocate_and_merge()
  │  → Merged payload (snapshot replaced, trend historized, lists appended)
  ▼
Saved as JSON to main/data/filtered-data/ (combined file)
Original file deleted from main/data/uploaded-data/
```
