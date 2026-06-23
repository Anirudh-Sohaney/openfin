# main.py

## Key Objective
Orchestrates the full subAgent5 pipeline: observes `main/Agent1/base-gens/` and `main/Agent1/insight-gens/` for JSON reports, converts unconverted ones to professional black-and-white PDFs, and saves them to `main/reports/base-reports/` and `main/reports/insights/`.

## Tools / Algorithms Used
- **data_access**: For loading JSON files from Agent1's intermediate directories, identifying existing PDFs in reports/, extracting report sections, and routing output paths.
- **pdf_generator**: For converting structured report data into professional B&W PDF documents using fpdf2 and pdf_template.json.
- **File I/O**: Directory scanning and path management.

## Key Objects

### `run() -> Dict[str, List[str]]`
- **Parameters**: None.
- **Use**: Main run function matching specs.md. Full pipeline: start observation, load sources, filter unconverted, generate PDFs, collect results, end observation.

### `start_observation()`
- **Parameters**: None.
- **Use**: Initialize observer, set activity status to idle.

### `end_observation()`
- **Parameters**: None.
- **Use**: End observation, set activity status to idle.

### `_step_load_sources() -> Dict[str, List[Dict]]`
- **Parameters**: None.
- **Use**: Scans `main/Agent1/base-gens/` and `main/Agent1/insight-gens/` for JSON files, checks which already have PDFs in `main/reports/`.

### `_step_filter_unconverted(sources) -> List[Dict]`
- **Parameters**: `sources` - output from `_step_load_sources()`.
- **Use**: Filters to only include source files without existing PDFs.

### `_step_generate_pdfs(unconverted) -> List[str]`
- **Parameters**: `unconverted` - list of source dicts needing PDF generation.
- **Use**: For each source: loads JSON, extracts sections, generates PDF via `pdf_generator.generate_report_pdf()`.

### `_step_collect_results(generated_paths) -> Dict[str, List[str]]`
- **Parameters**: `generated_paths` - list of generated PDF paths.
- **Use**: Organizes paths into `base_reports` and `insights` categories.

### `generate_single_pdf(json_file_path) -> Optional[str]`
- **Parameters**: `json_file_path` - path to a single JSON report/insight file.
- **Use**: Generate a PDF for a single JSON file on demand.

### `_set_activity(status: str)`
- **Parameters**: `status` - activity string ("generating pdf" or "idle").
- **Use**: Writes current activity to `log.txt` (overwrite mode, no history). Readable by Agent 1 for status tracking.

### `test()`
- **Parameters**: None.
- **Use**: Runs the pipeline with inline mock report data, bypassing file I/O. Prints parsed sections and template info. Invoked via `python3 -m main.Agent1.subAgent5.main --test`.
