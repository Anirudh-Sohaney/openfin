# llm_interface.py

## Key Objective
Interfaces with an LLM via OpenRouter API (OpenAI-compatible) to analyze dataset variables and determine which financial metrics can and should be derived. Falls back to heuristic analysis when the LLM is unavailable.

## Tools / Algorithms Used
- **OpenRouter API**: Free model `openai/gpt-oss-120b:free` (configurable via `LLM_MODEL` env var) for intelligent column mapping and metric identification. Includes `HTTP-Referer` and `X-Title` headers for OpenRouter ranking.
- **Heuristic fallback**: Pattern-matching on column names when LLM is unreachable.
- **Column mapping validation**: Post-processing safety checks that detect and correct common LLM mistakes (e.g., mapping monetary `sales_column` to a quantity column like `units_sold`). Also catches `quantity_column` accidentally mapped to revenue columns.
- **pandas**: For DataFrame inspection and column type analysis.

## Configuration (Environment Variables)
- `OPENAI_API_KEY` - Required. OpenRouter API key.
- `OPENAI_BASE_URL` - Base URL (default: `https://openrouter.ai/api/v1`).
- `LLM_MODEL` - Model name (default: `openai/gpt-oss-120b:free`). Supported free models also include `openrouter/owl-alpha`.

## Key Objects

### `ALL_KNOWN_METRICS: list[str]`
- **Use**: Master list of all ~80+ financial metrics that subAgent1 can potentially derive from data.

### `describe_dataframe(df: pd.DataFrame, date_col: Optional[str]) -> Dict`
- **Parameters**: `df` - DataFrame to describe; `date_col` - identified date column name.
- **Use**: Builds a structured JSON description of the DataFrame (columns, types, stats, sample rows) to send to the LLM.

### `build_analysis_prompt(data_description: Dict) -> str`
- **Parameters**: `data_description` - output from `describe_dataframe`.
- **Use**: Constructs the LLM prompt asking it to map columns and identify derivable metrics. Includes a "CRITICAL DISTINCTION" section that clarifies `sales_column` must be a monetary/revenue column (not a unit/quantity column) and that `quantity_column` must be a unit count column.

### `_validate_mappings(mappings: Dict) -> None`
- **Parameters**: `mappings` - column mappings dict from LLM response (mutated in-place).
- **Use**: Post-processes column mappings to fix common LLM mistakes. If `sales_column` equals `quantity_column`, clears `sales_column` so the calculator falls back to `revenue_column`. Also clears `sales_column` if its name contains quantity keywords (`units`, `qty`, `quantity`, `count`, `volume`). Symmetric check: clears `quantity_column` if it equals `revenue_column`. Prevents metrics like `total_sales` from being computed from unit counts instead of monetary values.

### `analyze_with_llm(df: pd.DataFrame, date_col: Optional[str]) -> Dict`
- **Parameters**: `df` - DataFrame; `date_col` - date column name.
- **Use**: Sends the DataFrame description to the LLM and parses the JSON response containing column mappings, derivable metrics, and timeframes.

### `heuristic_analysis(df: pd.DataFrame, date_col: Optional[str]) -> Dict`
- **Parameters**: `df` - DataFrame; `date_col` - date column name.
- **Use**: Fallback analysis using column-name pattern matching (no LLM required). Maps columns like "revenue", "profit", "customer_id" etc.

### `_make_json_safe(obj) -> object`
- **Parameters**: `obj` - any value (dict, list, Timestamp, etc.).
- **Use**: Recursively converts non-JSON-serializable objects (e.g., `pd.Timestamp`) to strings. Applied to sample rows before passing to LLM prompt.

### `analyze_dataframe(df: pd.DataFrame, date_col: Optional[str]) -> Dict`
- **Parameters**: `df` - DataFrame; `date_col` - date column name.
- **Use**: Main entry point. Attempts LLM analysis, applies `_validate_mappings` to catch column mapping errors, then falls back to heuristics on failure.
