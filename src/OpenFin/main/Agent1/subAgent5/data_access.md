# data_access.py

## Key Objective
Load JSON report and insight files from `main/Agent1/base-gens/` and `main/Agent1/insight-gens/`, identify which source files already have PDFs in `main/reports/`, and provide helper functions for subAgent5's PDF generation pipeline.

## Tools / Algorithms Used
- **JSON parsing**: Loads structured report data from both base-gens and insight-gens directories.
- **File I/O**: Scans directories for JSON/PDF files, extracts metadata, determines output paths.
- **Report section extraction**: Parses `{"Report Title": {"Section": "content", "_metadata": ...}}` uniformly — fields starting with `_` are treated as metadata.
- **Category routing**: Routes PDFs to `main/reports/base-reports/` or `main/reports/insights/` based on source category.

## Key Objects

### `BASE_GENS_DIR: str`
- **Use**: Path to `main/Agent1/base-gens/` — where subAgent2 saves report JSONs.

### `INSIGHT_GENS_DIR: str`
- **Use**: Path to `main/Agent1/insight-gens/` — where subAgents 3 and 4 save insight JSONs.

### `BASE_REPORTS_DIR: str`
- **Use**: Path to `main/reports/base-reports/` — where base report PDFs are saved.

### `INSIGHTS_DIR: str`
- **Use**: Path to `main/reports/insights/` — where insight PDFs are saved.

### `get_json_report_files() -> Dict[str, str]`
- **Parameters**: None.
- **Use**: Scans `main/Agent1/base-gens/` for JSON report files. Returns mapping of basename to full file path.

### `get_json_insight_files() -> Dict[str, str]`
- **Parameters**: None.
- **Use**: Scans `main/Agent1/insight-gens/` for JSON insight files. Returns mapping of basename to full file path.

### `get_existing_pdf_files(directory: str) -> set`
- **Parameters**: `directory` - path to scan for existing PDFs.
- **Use**: Returns set of basenames that already have PDFs in the given directory.

### `load_report_file(file_path: str) -> Optional[Dict]`
- **Parameters**: `file_path` - path to a JSON report/insight file.
- **Use**: Loads a single JSON file. Returns parsed dict or None on failure.

### `extract_report_sections(data: Dict) -> Tuple[str, Dict[str, str], str, str]`
- **Parameters**: `data` - loaded JSON dict.
- **Use**: Extracts report title, content sections (filtering `_metadata` fields), source_file, and generated_at timestamp.

### `pdf_output_path_for(source_category: str, basename: str) -> str`
- **Parameters**: `source_category` - "base-report" or "insight"; `basename` - filename without extension.
- **Use**: Returns the appropriate output PDF path in `main/reports/` based on source category.
