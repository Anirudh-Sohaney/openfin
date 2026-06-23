# subAgent1 — Directory Documentation

## Key Objective
Process user prompts and provide subAgent 2 with the data it needs to respond as a financial advisor chatbot. subAgent 1 identifies what data is required, retrieves it from the correct source (filtered-data JSONs, base-reports PDFs, insights PDFs, or internet/Tavily), and returns it along with metadata about what was found.

## Data Sources

| Source | Format | Path | Content |
|--------|--------|------|---------|
| `filtered-data` | JSON | `main/data/filtered-data/` | Structured financial metrics (revenue, sales, expenses, growth rates, etc.) |
| `base-reports` | PDF | `main/reports/base-reports/` | Professional narrative reports (Revenue, P&L, Financial Health, etc.) with Executive Summary, Analysis, Conclusions |
| `insights` | PDF | `main/reports/insights/` | Research-driven analysis reports (pricing optimization, cost reduction, market opportunities, risk assessment) |
| `internet` | Web | Tavily API | Live web search for external information (suppliers, competitors, market trends) |

**Fallback:** If no PDFs are found in `base-reports/` or `insights/`, subAgent 1 falls back to the original JSON source files in `main/Agent1/base-gens/` and `main/Agent1/insight-gens/`.

## Key Initiating Function / Call Process

The main run function is `main.run(user_prompt)`:

```
main.run(user_prompt)
  ├─ [LLM Call] prompt_analyzer.analyze_prompt()
  │     → identifies data_source, keywords, required_data_fields
  └─ data_retriever.retrieve_data()
        ├─ If filtered-data: load JSON from main/data/filtered-data/
        ├─ If base-reports: extract text from PDFs in main/reports/base-reports/
        │                    (fallback: JSONs in main/Agent1/base-gens/)
        ├─ If insights: extract text from PDFs in main/reports/insights/
        │               (fallback: JSONs in main/Agent1/insight-gens/)
        └─ If internet: Tavily web search
```

The result is a structured dict containing:
- `analysis`: What data source, keywords, and specific fields were identified
- `data`: Raw metrics, specifically extracted fields, and content from the source

## Uses Exactly 1 LLM Call
The single LLM call analyzes the user prompt to determine:
- Which data source to query (filtered-data, base-reports, insights, or internet)
- Which keywords to use for relevance ranking
- Which specific metric/field names to extract

Data retrieval and extraction are purely programmatic.

## Tools / Algorithms Used
- **OpenRouter API (gpt-oss-120b:free)**: Single LLM call for prompt analysis.
- **pypdf (v6.x)**: Extracts text from PDF reports in `base-reports/` and `insights/` directories. Parses raw text into structured sections by heuristic heading detection.
- **Local JSON file loading**: Scans `filtered-data/`, `base-gens/`, `insight-gens/` directories with keyword-frequency ranking.
- **Tavily API**: Web search for external/supplier/market research queries.
- **Specific field extraction**: Extracts exactly the metric fields requested by the LLM call; missing fields are returned as `null` for subAgent 2 to handle.
- **Keyword frequency scoring**: Ranks documents by total occurrence count of keywords for best-match selection.

## PDF Text Extraction
PDF reports are parsed heuristically:
1. **Title detection**: First long line is identified as the report title.
2. **Heading detection**: Lines matching known heading patterns (e.g., "Executive Summary", "Data", "Analysis", "Risk Assessment") or Title Case patterns are treated as section headings.
3. **Content grouping**: Text between headings is grouped under the preceding heading.
4. **Footer stripping**: Page numbers ("Page X of Y") and confidentiality markers are filtered out.
5. **Section matching**: Keyword relevance is computed on the extracted text to find the most relevant report.

## Major Files

| File | Purpose |
|------|---------|
| `prompt_analyzer.py` | [1 LLM Call] Analyzes user prompt to determine data source, keywords, and required fields |
| `data_retriever.py` | Retrieves data from local JSON files, PDF files (via pypdf), or Tavily web search; supports PDF text extraction and specific field extraction |
| `main.py` | Orchestrates: analyze prompt → retrieve data → return result |

## Major Functions / Classes

| File | Object | Parameters | Use |
|------|--------|------------|-----|
| prompt_analyzer | `analyze_prompt(user_prompt)` | `user_prompt: str` | [LLM Call] Determine data_source, keywords, required_data_fields |
| data_retriever | `retrieve_data(analysis)` | `analysis: dict` | Fetch data from source (JSON or PDF); extract specific fields if requested |
| data_retriever | `_load_filtered_data(keywords, fields)` | `keywords, fields` | Load JSON metrics from main/data/filtered-data/ |
| data_retriever | `_load_base_reports(keywords)` | `keywords: list` | Load PDF reports from main/reports/base-reports/ (with JSON fallback) |
| data_retriever | `_load_insights(keywords)` | `keywords: list` | Load PDF insights from main/reports/insights/ (with JSON fallback) |
| data_retriever | `_extract_pdf_text(pdf_path)` | `pdf_path: str` | Extract text from a PDF file using pypdf; parse into sections |
| data_retriever | `_parse_pdf_text_into_sections(text)` | `text: str` | Parse raw PDF text into heading → content dict |
| data_retriever | `_load_pdf_files(directory)` | `directory: str` | Load all PDFs in a directory and return parsed text |
| data_retriever | `_extract_specific_fields(metrics, fields)` | `metrics, fields` | Extract only the metric fields identified as necessary; missing fields return null |
| data_retriever | `_keyword_match_text(text, keywords)` | `text, keywords` | Count keyword occurrences in a plain text string (used for PDF content) |
| main | `run(user_prompt)` | `user_prompt: str` | Main entry point: analyze → retrieve → return structured result |

## Data Flow

```
User prompt (string)
  │
  ▼
[LLM Call] prompt_analyzer.analyze_prompt()
  │ → { data_source, data_keywords, required_data_fields, summary }
  ▼
data_retriever.retrieve_data()
  │
  ├── filtered-data  →  JSON files (main/data/filtered-data/)
  ├── base-reports   →  PDF files (main/reports/base-reports/) [+ JSON fallback]
  ├── insights       →  PDF files (main/reports/insights/) [+ JSON fallback]
  └── internet       →  Tavily API search
  │
  ▼
Structured dict returned to Agent 2 for subAgent 2 consumption
```
