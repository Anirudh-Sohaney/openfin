# data_retriever.py

## Key Objective
Fetch data from the appropriate source based on the LLM call's analysis. Supports four sources: local filtered-data JSON files, base-reports PDF files, insights PDF files, and internet search via Tavily API. Extracts specific metric fields identified by the LLM call. For PDF sources, uses pypdf to extract text and parse it into structured sections.

## Tools / Algorithms Used
- **JSON file I/O**: Loads and parses JSON files from `main/data/filtered-data/`, `main/Agent1/base-gens/`, and `main/Agent1/insight-gens/`.
- **pypdf (v6.x)**: Extracts text content from PDF files in `main/reports/base-reports/` and `main/reports/insights/`.
- **Heuristic PDF text parsing**: Detects section headings in extracted PDF text by matching known heading patterns (e.g., "Executive Summary", "Data", "Analysis") and Title Case patterns. Groups text under headings. Strips page numbers and footer markers.
- **Keyword frequency scoring**: Ranks documents (both JSON and PDF) by total occurrence count of keywords for best-match selection.
- **Specific field extraction**: When `required_data_fields` is provided, extracts only those field values from JSON data. Missing fields are returned as `null` for downstream handling of insufficiency.
- **Tavily API**: For internet search queries.
- **Fallback chain**: If no PDFs are found in `base-reports/` or `insights/`, falls back to JSON source files in `base-gens/` and `insight-gens/`.

## Key Objects

### `retrieve_data(analysis: Dict) -> Dict`
- **Parameters**: `analysis` - Dict from prompt_analyzer with data_source, data_keywords, required_data_fields, tavily_query.
- **Use**: Routes to the correct retrieval function. Falls back through sources if primary source has no results.

### `_load_filtered_data(keywords, required_fields) -> Optional[Dict]`
- **Parameters**: `keywords` - Keywords to match; `required_fields` - Specific fields to extract.
- **Use**: Loads and ranks JSON files from `filtered-data/`. Extracts both keyword-matched sections and specific requested fields.

### `_load_base_reports(keywords) -> Optional[Dict]`
- **Parameters**: `keywords` - Keywords to match.
- **Use**: Loads and ranks PDF files from `main/reports/base-reports/` using pypdf text extraction. Falls back to JSON files in `base-gens/`.

### `_load_insights(keywords) -> Optional[Dict]`
- **Parameters**: `keywords` - Keywords to match.
- **Use**: Loads and ranks PDF files from `main/reports/insights/` using pypdf text extraction. Falls back to JSON files in `insight-gens/`.

### `_extract_pdf_text(pdf_path: str) -> Dict[str, str]`
- **Parameters**: `pdf_path` - Path to the PDF file.
- **Use**: Uses pypdf to extract all text from the PDF, then parses it into a dict of `{section_heading: section_content}`. The report title is stored under `_report_title` key.

### `_parse_pdf_text_into_sections(full_text: str) -> Dict[str, str]`
- **Parameters**: `full_text` - Raw text extracted from a PDF.
- **Use**: Parses raw text into structured sections. Detects headings heuristically: lines matching known heading names (from `_KNOWN_HEADINGS` list) or Title Case patterns. Strips page numbers and footer markers.

### `_load_pdf_files(directory: str) -> List[Dict]`
- **Parameters**: `directory` - Directory path to scan for PDF files.
- **Use**: Scans a directory for `.pdf` files, extracts text from each, and returns them in a format compatible with the existing ranking/extraction pipeline (`filename`, `filepath`, `data` keys).

### `_keyword_match_text(text: str, keywords: List[str]) -> int`
- **Parameters**: `text` - Plain text to search; `keywords` - Keywords to count.
- **Use**: Counts keyword occurrences in a plain text string. Used for PDF-based content ranking.

### `_extract_specific_fields(metrics, required_fields) -> Dict`
- **Parameters**: `metrics` - Dict of available metrics; `required_fields` - Field names to extract.
- **Use**: Returns only the requested fields. Any field not present in the data is set to `null`, enabling subAgent 2 to detect insufficient data.

### `_find_metrics_container(data) -> Optional[Dict]`
- **Parameters**: `data` - Loaded JSON data.
- **Use**: Finds the metrics dict regardless of key name (`computed_metrics`, `_metrics_used`, or `metrics`).

### `_search_internet(query) -> Optional[Dict]`
- **Parameters**: `query` - Search query string.
- **Use**: Performs Tavily web search.

### `_load_json_files(directory: str) -> List[Dict]`
- **Parameters**: `directory` - Directory path to scan for JSON files.
- **Use**: Scans a directory for `.json` files, loads and parses each, and returns a list of `{filename, filepath, data}` dicts.

### `_extract_relevant_data(file_data, keywords, required_fields) -> Dict`
- **Parameters**: `file_data` - File entry dict from `_load_json_files` or `_load_pdf_files`; `keywords` - Keywords to match; `required_fields` - Specific fields to extract (optional).
- **Use**: Extracts relevant data from a single file entry. Automatically detects whether the data is JSON-based (nested metrics) or PDF-based (flat text sections) and applies the appropriate extraction logic.

### `_extract_json_sections(data: Dict, keywords: List[str]) -> List[Dict]`
- **Parameters**: `data` - Loaded JSON data dict; `keywords` - Keywords to match.
- **Use**: Scans JSON keys and values for keyword matches and returns a list of `{heading, content}` dicts for the matching sections.

### `_extract_pdf_relevant_data(pdf_data: Dict, keywords: List[str]) -> Dict`
- **Parameters**: `pdf_data` - PDF-parsed data entry; `keywords` - Keywords to match.
- **Use**: Extracts relevant sections from PDF data by matching keywords against section headings and content. Returns the same structure as `_extract_relevant_data` but without structured metrics.

### `_keyword_match(entry: Dict, keywords: List[str]) -> int`
- **Parameters**: `entry` - File entry dict with `data` key; `keywords` - Keywords to count.
- **Use**: Counts keyword occurrences across the full JSON-serialized or string content of a file entry. Works for both JSON and PDF-sourced data.

### `_rank_by_relevance(files: List[Dict], keywords: List[str]) -> List[Dict]`
- **Parameters**: `files` - List of file entry dicts; `keywords` - Keywords to rank by.
- **Use**: Sorts file entries by total keyword occurrence count (highest first), adding a `_relevance` key to each entry.

### `_KNOWN_HEADINGS` (module-level list)
- **Use**: List of known section heading keywords (e.g., "executive summary", "analysis", "risk assessment") used by `_is_heading()` to heuristically detect section boundaries in extracted PDF text.

### `METRICS_CONTAINER_KEYS` (module-level list)
- **Use**: List of possible key names (`_metrics_used`, `computed_metrics`, `metrics`) that may contain the metrics dict in JSON data. Used by `_find_metrics_container()` to locate metrics regardless of key naming.

## Directory Constants

| Constant | Path | Content |
|----------|------|---------|
| `FILTERED_DATA_DIR` | `main/data/filtered-data/` | JSON metrics |
| `BASE_REPORTS_DIR` | `main/reports/base-reports/` | PDF reports |
| `INSIGHTS_DIR` | `main/reports/insights/` | PDF insights |
| `BASE_GENS_DIR` | `main/Agent1/base-gens/` | JSON report sources (fallback) |
| `INSIGHT_GENS_DIR` | `main/Agent1/insight-gens/` | JSON insight sources (fallback) |

## PDF Parsing Details

The heuristic heading detector (`_is_heading()`) considers a line a heading if it:
1. Is 5-80 characters long
2. Does not end with sentence-ending punctuation (.!?:)
3. Is not a page number or confidentiality footer
4. Either matches a known heading name from `_KNOWN_HEADINGS`, or matches a Title Case pattern like "Risk Assessment", or matches a numbered pattern like "1. Recommendation"
