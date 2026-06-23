# subAgent5 — Directory Documentation

## Key Objective
Converts JSON reports from other subAgents into professional black-and-white PDFs. Reads report JSONs from `main/Agent1/base-gens/` (subAgent2 output) and insight JSONs from `main/Agent1/insight-gens/` (subAgent3/subAgent4 output), converts them using the layout defined in `pdf_template.json`, and saves PDFs to `main/reports/base-reports/` and `main/reports/insights/` respectively.

## Key Initiating Function / Call Process

The main run function is `main.run()`:

```
main.run()
  ├─ start_observation()         # Sets activity to idle, ready to watch
  │
  ├─ _step_load_sources()
  │    ├─ data_access.get_json_report_files()    → main/Agent1/base-gens/*.json
  │    ├─ data_access.get_json_insight_files()   → main/Agent1/insight-gens/*.json
  │    └─ data_access.get_existing_pdf_files()   → check reports/ for .pdf counterparts
  │
  ├─ _step_filter_unconverted()
  │    └─ Keep only sources without PDFs
  │
  ├─ _step_generate_pdfs()
  │    └─ For each unconverted source:
  │         ├─ data_access.load_report_file()
  │         ├─ data_access.extract_report_sections()
  │         └─ pdf_generator.generate_report_pdf()
  │              ├─ Title at top of first page
  │              ├─ Metadata line (source | date | classification)
  │              ├─ Section headings & body text
  │              └─ Page numbers in footer
  │
  ├─ _step_collect_results()
  │    └─ Return { "base_reports": [...], "insights": [...] }
  │
  └─ end_observation()           # Sets activity back to idle
```

## Tools / Algorithms Used

- **fpdf2**: Lightweight Python PDF generation library with DejaVu font support.
- **pdf_template.json**: External layout configuration — all margins, fonts, colors, spacing defined in JSON. Purely algorithmic, no LLM calls.
- **Black & white only**: All colors limited to black, dark grey, grey, light grey, white.
- **No cover page**: Title sits at top of the first content page with a separator line and metadata.
- **Automatic heading detection**: Section names parsed for heading levels (e.g., "1. Executive Summary" → level 1).

## Major Files

| File | Purpose |
|------|---------|
| `pdf_template.json` | PDF layout template — all styling/formatting constants defined here |
| `data_access.py` | Loads JSONs from base-gens/insight-gens; detects existing PDFs; extracts sections |
| `pdf_generator.py` | fpdf2-based B&W PDF generation, driven by pdf_template.json |
| `main.py` | Orchestrates the full pipeline: observe → load → filter → generate → collect |

## Major Functions / Classes

| File | Object | Parameters | Use |
|------|--------|------------|-----|
| data_access | `get_json_report_files()` | None | Scan main/Agent1/base-gens/ for JSON files |
| data_access | `get_json_insight_files()` | None | Scan main/Agent1/insight-gens/ for JSON files |
| data_access | `get_existing_pdf_files(dir)` | `dir: str` | Check for existing PDFs in output directory |
| data_access | `load_report_file(path)` | `path: str` | Load single JSON report/insight |
| data_access | `extract_report_sections(data)` | `data: dict` | Parse title, sections, metadata |
| data_access | `pdf_output_path_for(category, name)` | `category: str, name: str` | Route PDF to correct reports/ subdirectory |
| pdf_generator | `generate_report_pdf(title, sections, source, ts, path)` | `title: str, sections: dict, source: str, ts: str, path: str` | Generate B&W PDF from template |
| pdf_generator | `_write_title_header(pdf, title, source, ts)` | `pdf: FPDF, title: str, source: str, ts: str` | Title + separator + metadata line |
| pdf_generator | `_write_heading(pdf, text, level)` | `pdf: FPDF, text: str, level: int` | Formatted section heading |
| main | `run()` | None | Main entry: full pipeline |
| main | `start_observation()` | None | Initialize observer, set activity to idle |
| main | `end_observation()` | None | End observation, set activity to idle |
| main | `generate_single_pdf(json_path)` | `json_path: str` | Generate PDF for a single JSON file |
| main | `test()` | None | Run pipeline with inline mock data, print results |

## PDF Layout (from template)
- **Title**: 20pt bold black, with 0.6mm separator line underneath
- **Metadata line**: 8pt italic grey — `source_file | generated_at | classification`
- **Headings**: Level 1 (14pt bold black, with separator), Level 2 (12pt bold dark grey), Level 3 (11pt bold italic black)
- **Body**: 10pt regular black, 5.5mm line height
- **Footer**: "Page X of Y" in 8pt italic grey
- **Colors**: Black, dark grey, grey, light grey, white only

## Data Flow

```
Source JSONs                         Output PDFs
─────────────────────────            ────────────────────────
main/Agent1/base-gens/*.json   →    main/reports/base-reports/*.pdf
main/Agent1/insight-gens/*.json →   main/reports/insights/*.pdf
```
