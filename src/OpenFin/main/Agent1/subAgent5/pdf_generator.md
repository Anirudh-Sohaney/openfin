# pdf_generator.py

## Key Objective
Converts structured JSON report/insight data into professional black-and-white PDF documents using fpdf2. All layout parameters are driven by `pdf_template.json` — no LLM calls, purely algorithmic generation.

## Tools / Algorithms Used
- **fpdf2**: Lightweight Python PDF generation library. Handles Unicode text via DejaVu fonts, auto page breaking, and multi-cell text wrapping.
- **pdf_template.json**: External layout configuration defining all margins, font sizes, colors, spacing, and structural elements.
- **Heading level detection**: Parses section names (e.g., "1. Executive Summary") to determine heading levels automatically.

## Key Objects

### `generate_report_pdf(report_title, sections, source_file, generated_at, output_path) -> str`
- **Parameters**: `report_title: str` - title of the report; `sections: dict` - section heading → content; `source_file: str` - data source filename; `generated_at: str` - ISO timestamp; `output_path: str` - destination path.
- **Use**: Main entry point. Creates a B&W PDF with title at top, metadata line, formatted sections, and page numbering.

### `_write_title_header(pdf, report_title, source_file, generated_at)`
- **Parameters**: `pdf: FPDF`; `report_title: str`; `source_file: str`; `generated_at: str`.
- **Use**: Writes the bold title, a separator line, and the metadata line (source | date | classification) at the top of the first page.

### `_write_heading(pdf, text, level)`
- **Parameters**: `pdf: FPDF`; `text: str`; `level: int` (1-3).
- **Use**: Writes a section heading with formatting from template (font size, style, color, spacing, optional separator line).

### `_write_text(pdf, text, style, size, color_name, align, line_h)`
- **Parameters**: `pdf: FPDF`; `text: str`; styling options.
- **Use**: Writes a block of text with word wrapping and consistent formatting.

### `_detect_heading_level(section_name: str) -> int`
- **Parameters**: `section_name: str` - e.g., "1. Executive Summary" or "Revenue Overview".
- **Use**: Detects heading level from section name. Numbered patterns ("1.", "1.1") map to corresponding levels; unnumbered sections default to level 2.

### `_load_template() -> Dict`
- **Parameters**: None.
- **Use**: Loads and caches `pdf_template.json` for all layout configuration.

## PDF Layout (from template)
- **Title**: 20pt bold black at top of first page, with 0.6mm separator line
- **Metadata line**: 8pt italic grey — source file | date | classification
- **Headings**: Level 1 (14pt bold), Level 2 (12pt bold dark grey), Level 3 (11pt bold italic)
- **Body text**: 10pt regular black, 5.5mm line height
- **Footer**: "Page X of Y" in 8pt italic grey
- **Colors**: Black, dark grey, grey, light grey only — no color
