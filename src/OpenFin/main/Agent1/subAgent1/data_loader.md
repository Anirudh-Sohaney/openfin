# data_loader.py

## Key Objective
Accepts all spreadsheet formats (CSV, XLSX, XLS, ODS, TSV) and converts them into analyzable pandas DataFrames with automatic standardization and date column detection.

## Tools / Algorithms Used
- **pandas**: Primary library for data loading, transformation, and type inference.
- **openpyxl / xlrd / odf**: Excel/ODS engines for reading spreadsheet formats.
- **Numeric extraction regex**: Extracts first numeric value from mixed strings (e.g., "100 items" → "100").
- **Chained str.replace**: Simple literal replacement for currency symbols ($, €, £, ¥, %, \\) and commas — avoids regex escaping issues.
- **Pattern matching**: Heuristic column-name matching for date column identification.

## Key Objects

### `detect_file_format(file_path: str) -> str`
- **Parameters**: `file_path` - path to spreadsheet file.
- **Use**: Maps file extension to a standardized format string (`csv`, `xlsx`, `xls`, `ods`, `tsv`).

### `load_single_file(file_path: str) -> pd.DataFrame`
- **Parameters**: `file_path` - path to spreadsheet file.
- **Use**: Loads a single file into a DataFrame, handling encoding fallbacks and TSV auto-detection.

### `standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame`
- **Parameters**: `df` - raw DataFrame.
- **Use**: Cleans column names, drops empty rows/cols. Attempts numeric conversion for object/string columns by: (1) stripping currency symbols ($, €, £, ¥, %) and backslashes via literal `str.replace`, (2) removing commas, (3) extracting the first numeric value from mixed text via regex `(-?\d+\.?\d*)`, then converting via `pd.to_numeric`. Handles both `object` and `StringDtype` columns.

### `identify_date_column(df: pd.DataFrame) -> Optional[str]`
- **Parameters**: `df` - standardized DataFrame.
- **Use**: Identifies the primary date column by checking datetime dtypes first, then pattern-matching column names.

### `load_and_prepare(file_path: str) -> Tuple[pd.DataFrame, Optional[str]]`
- **Parameters**: `file_path` - path to spreadsheet file.
- **Use**: Main entry point. Loads, standardizes, and identifies the date column in one call.

### `load_all_from_directory(directory: str) -> list`
- **Parameters**: `directory` - path to directory containing spreadsheets.
- **Use**: Batch-loads all supported files from a directory.
