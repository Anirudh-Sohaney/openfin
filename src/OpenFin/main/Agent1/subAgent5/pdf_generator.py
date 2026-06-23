"""
pdf_generator.py
Key objective: Convert structured JSON report/insight data into professional
black-and-white PDF documents using fpdf2, driven by pdf_template.json.

The template defines all layout constants. This module reads the template
and applies it algorithmically — no LLM calls.

Design:
  - Title at top of first page (no separate cover page)
  - Black & white only
  - Metadata line below title
  - Section headings with levels and separator lines
  - Page numbers in footer
"""
import os
import re
import json
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional

from fpdf import FPDF


# ── Template loading ────────────────────────────────────

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "pdf_template.json")

_template_cache: Optional[Dict[str, Any]] = None


def _load_template() -> Dict[str, Any]:
    """Load pdf_template.json, with caching."""
    global _template_cache
    if _template_cache is not None:
        return _template_cache
    with open(TEMPLATE_PATH, "r") as f:
        _template_cache = json.load(f)
    return _template_cache


def _cfg(*keys: str) -> Any:
    """Shorthand: get nested value from template by path of keys."""
    t = _load_template()
    for k in keys:
        t = t.get(k, {})
    return t


def _color(name: str) -> tuple:
    """Get RGB tuple for a named color from template."""
    rgb = _cfg("colors", name)
    return tuple(rgb) if rgb else (0, 0, 0)


# ── Font setup ──────────────────────────────────────────

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_use_dejavu = False


def _cleanse_text(text: str) -> str:
    """
    Replace Unicode characters with ASCII equivalents for Helvetica fallback.

    Two-pass strategy:
      1. Curated map covers punctuation, dashes, spaces, and zero-width chars
         commonly produced by LLMs (notably the U+2011 non-breaking hyphen
         that breaks words like `subscription-based` in PDFs).
      2. `unicodedata.normalize('NFKD', ...)` decomposes any remaining
         compatibility characters, then combining marks are dropped. As a
         final safety net, any leftover non-ASCII char falls back to '?'.
    """
    replacements = {
        '\u2014': '--',     # em dash
        '\u2013': '-',      # en dash
        '\u2011': '-',      # non-breaking hyphen (subscription\u2011based)
        '\u2010': '-',      # hyphen
        '\u2012': '-',      # figure dash
        '\u2015': '--',     # horizontal bar
        '\u2212': '-',      # minus sign
        '\u2018': "'",      # left single quote
        '\u2019': "'",      # right single quote / apostrophe
        '\u201c': '"',      # left double quote
        '\u201d': '"',      # right double quote
        '\u201a': ',',      # single low-9 quote
        '\u201e': '"',      # double low-9 quote
        '\u2032': "'",      # prime
        '\u2033': '"',      # double prime
        '\u2039': '<',      # single left angle quote
        '\u203a': '>',      # single right angle quote
        '\u2026': '...',    # horizontal ellipsis
        '\u00a0': ' ',      # non-breaking space
        '\u2009': ' ',      # thin space
        '\u202f': ' ',      # narrow no-break space
        '\u200b': '',       # zero-width space
        '\u200c': '',       # zero-width non-joiner
        '\u200d': '',       # zero-width joiner
        '\u2060': '',       # word joiner
        '\ufeff': '',       # BOM / zero-width no-break space
        '\u00ad': '',       # soft hyphen
        '\u2022': '-',      # bullet
        '\u25cf': '-',      # black circle
        '\u2219': '\u00b7', # bullet operator
        '\u2122': '(TM)',   # trademark
        '\u00ae': '(R)',    # registered
        '\u00a9': '(C)',    # copyright
        '\u00d7': 'x',      # multiplication sign
        '\u00f7': '/',      # division sign
        '\u2264': '<=',     # less than or equal
        '\u2265': '>=',     # greater than or equal
        '\u2248': '~',      # almost equal to
        '\u2020': '+',      # dagger
        '\u2021': '++',     # double dagger
        '\u02c6': '^',      # modifier letter circumflex
        '\u2030': '/1000',  # per mille sign
        '\u20ac': 'EUR',    # euro
        '\u00a3': 'GBP',    # pound
        '\u00a5': 'JPY',    # yen
    }
    # Pass 1: apply curated replacements. Unknown chars drop rather than
    # become '?' so NFKD in pass 2 has a chance to compose them.
    phase1 = []
    for ch in text:
        if ord(ch) < 128:
            phase1.append(ch)
        else:
            phase1.append(replacements.get(ch, ''))
    phase1 = ''.join(phase1)

    # Pass 2: NFKD normalize to decompose ligatures/compatibility chars,
    # then drop combining marks (accents, etc.).
    normalized = unicodedata.normalize('NFKD', phase1)
    stripped = ''.join(ch for ch in normalized if not unicodedata.combining(ch))

    # Pass 3: any still non-ASCII char becomes '?' so FPDF doesn't choke.
    return ''.join(ch if ord(ch) < 128 else '?' for ch in stripped)


# ── Markdown stripping ──────────────────────────────────
#
# Patterns use look-arounds so that arithmetic (`5 * 3 = 15`) and
# snake_case identifiers (`total_revenue_total_expenses`) are NOT falsely
# stripped. Bold tokens (`**...**`) are processed before italic (`*...*`)
# so we don't accidentally consume nested markers.

_MARKDOWN_PATTERNS = [
    (re.compile(r'\*\*(?=\S)(.+?)(?<=\S)\*\*'), r'\1'),   # **bold** (no whitespace boundary)
    (re.compile(r'__(?=\S)(.+?)(?<=\S)__'),     r'\1'),   # __bold__
    (re.compile(r'(?<!\w)\*(?=\S)(.+?)(?<=\S)\*(?!\w)'), r'\1'),  # *italic*
    (re.compile(r'(?<![\w])_(?=\S)(.+?)(?<=\S)_(?![\w])'), r'\1'),  # _italic_ (excludes snake_case)
    (re.compile(r'`([^`]+?)`'),                  r'\1'),   # `code`
    (re.compile(r'~~(?=\S)(.+?)(?<=\S)~~'),      r'\1'),   # ~~strike~~
]


def _strip_markdown(text: str) -> str:
    """
    Strip common Markdown inline markers so they don't render as literal
    `**` / `*` / `_` characters in the PDF. Uses word-boundary look-arounds
    so arithmetic (`5 * 3`) and snake_case column names (`total_revenue`)
    are preserved.
    """
    if not text:
        return text
    for pattern, replacement in _MARKDOWN_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _sanitize_sections(sections: Dict[str, str]) -> Dict[str, str]:
    """Sanitize all section keys and content for Helvetica compatibility if needed."""
    if _use_dejavu:
        return sections
    return {_cleanse_text(k): _cleanse_text(v) for k, v in sections.items()}


def _ensure_fonts():
    """Ensure DejaVu fonts are available locally. Falls back to Helvetica."""
    global _use_dejavu

    font_names = [
        "DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans-Oblique.ttf",
        "DejaVuSans-BoldOblique.ttf",
    ]

    os.makedirs(FONT_DIR, exist_ok=True)

    # Check if all fonts are already on disk
    all_present = all(
        os.path.isfile(os.path.join(FONT_DIR, fn)) and os.path.getsize(os.path.join(FONT_DIR, fn)) > 1000
        for fn in font_names
    )
    if all_present:
        _use_dejavu = True
        return

    # Try pkgutil extraction from fpdf2
    for fname in font_names:
        dst = os.path.join(FONT_DIR, fname)
        if os.path.isfile(dst) and os.path.getsize(dst) > 1000:
            continue
        try:
            import pkgutil
            data = pkgutil.get_data("fpdf", f"font/{fname}")
            if data and len(data) > 1000:
                with open(dst, "wb") as fh:
                    fh.write(data)
        except Exception:
            pass

    if all(
        os.path.isfile(os.path.join(FONT_DIR, fn)) and os.path.getsize(os.path.join(FONT_DIR, fn)) > 1000
        for fn in font_names
    ):
        _use_dejavu = True
    # else: _use_dejavu stays False, Helvetica fallback + text sanitizer used


def _make_pdf() -> FPDF:
    """Create a configured FPDF instance for an A4 B&W document."""
    t = _load_template()
    pg = t["page"]

    pdf = FPDF(
        orientation=pg.get("orientation", "P"),
        unit=pg.get("unit", "mm"),
        format=pg.get("format", "A4"),
    )
    pdf.set_auto_page_break(auto=True, margin=pg["margin_bottom"])
    pdf.add_page()

    if _use_dejavu:
        pdf.add_font("ReportFont", "", os.path.join(FONT_DIR, "DejaVuSans.ttf"), uni=True)
        pdf.add_font("ReportFont", "B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"), uni=True)
        pdf.add_font("ReportFont", "I", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf"), uni=True)
        pdf.add_font("ReportFont", "BI", os.path.join(FONT_DIR, "DejaVuSans-BoldOblique.ttf"), uni=True)
    else:
        pdf.set_font("Helvetica", "", 10)

    return pdf


def _set_font(pdf: FPDF, style: str = "", size: int = 10):
    """Set font, using DejaVu if available or Helvetica fallback."""
    if _use_dejavu:
        pdf.set_font("ReportFont", style, size)
    else:
        helv = style if style != "BI" else "B"
        pdf.set_font("Helvetica", helv, size)


# ── PDF building helpers ────────────────────────────────

def _content_width() -> float:
    pg = _cfg("page")
    return pg["width_mm"] - pg["margin_left"] - pg["margin_right"]


def _margin_left() -> float:
    return _cfg("page", "margin_left")


def _draw_separator(pdf: FPDF, thickness_mm: float, y_pad_mm: float = 0):
    """Draw a horizontal separator line across the content area."""
    c = _color("light_grey")
    pdf.set_draw_color(*c)
    pdf.set_line_width(thickness_mm)
    x = _margin_left()
    w = _content_width()
    y = pdf.get_y() + y_pad_mm
    pdf.line(x, y, x + w, y)
    pdf.set_y(y + 0.5)


def _sanitize(text: str) -> str:
    """Sanitize text for Helvetica compatibility. Passes through if DejaVu available."""
    if _use_dejavu:
        return text
    return _cleanse_text(text)


def _write_text(
    pdf: FPDF,
    text: str,
    style: str = "",
    size: int = 10,
    color_name: str = "black",
    align: str = "L",
    line_h: float = 5.5,
):
    """Write a text block with word wrapping. Strips Markdown and sanitizes Unicode."""
    _set_font(pdf, style, size)
    pdf.set_text_color(*_color(color_name))
    # Always strip Markdown markers first (works regardless of font choice),
    # then fall back to Unicode cleanse if DejaVu isn't available.
    pdf.multi_cell(w=_content_width(), h=line_h, text=_sanitize(_strip_markdown(text)), align=align)


def _write_heading(pdf: FPDF, text: str, level: int = 1):
    """Write a section heading per template heading_levels config."""
    hl = _cfg("content", "heading_levels", str(level))
    if not hl:
        # Fallback for unknown levels
        _write_text(pdf, text, style="B", size=12, color_name="black")
        return

    # Check page space
    page_h = _cfg("page", "height_mm")
    margin_b = _cfg("page", "margin_bottom")
    if pdf.get_y() > page_h - margin_b - 25:
        pdf.add_page()

    before = hl.get("spacing_before_mm", 4)
    after = hl.get("spacing_after_mm", 2)

    pdf.ln(before)
    _write_text(
        pdf,
        text,
        style=hl.get("style", "B"),
        size=hl.get("font_size", 12),
        color_name="black" if level <= 1 else "dark_grey",
        line_h=hl.get("line_height_mm", 6),
    )
    pdf.ln(after)

    if hl.get("separator_line", False):
        _draw_separator(pdf, 0.3, y_pad_mm=1)
        pdf.ln(2)


# ── Title header + metadata ─────────────────────────────

def _write_title_header(pdf: FPDF, report_title: str, source_file: str, generated_at: str):
    """
    Write the report title at the top of the first page, followed by
    a separator line and metadata line.
    """
    th = _cfg("title_header")
    if not th.get("enabled", True):
        return

    # Title
    _write_text(
        pdf,
        report_title,
        style=th.get("style", "B"),
        size=th.get("font_size", 20),
        color_name="black",
        line_h=th.get("line_height_mm", 10),
    )

    # Separator line
    if th.get("separator_line", True):
        t_mm = th.get("separator_thickness_mm", 0.6)
        _draw_separator(pdf, t_mm, y_pad_mm=0)

    pdf.ln(th.get("spacing_after_mm", 6))

    # Metadata line
    ml = _cfg("metadata_line")
    if ml.get("enabled", True):
        parts = []
        fields = ml.get("fields", [])
        for field in fields:
            if field == "source_file" and source_file:
                parts.append(source_file)
            elif field == "generated_at" and generated_at:
                try:
                    dt = datetime.fromisoformat(generated_at)
                    parts.append(dt.strftime("%B %d, %Y"))
                except (ValueError, TypeError):
                    parts.append(generated_at)
            elif field == "classification":
                parts.append(_cfg("classification_text"))
        if parts:
            sep = ml.get("label_separator", " | ")
            _write_text(
                pdf,
                sep.join(parts),
                style=ml.get("style", "I"),
                size=ml.get("font_size", 8),
                color_name="grey",
                line_h=4,
            )
        pdf.ln(ml.get("spacing_after_mm", 8))


# ── Main generation ─────────────────────────────────────

def generate_report_pdf(
    report_title: str,
    sections: Dict[str, str],
    source_file: str = "",
    generated_at: str = "",
    output_path: str = "",
) -> str:
    """
    Generate a professional black-and-white PDF report.

    Creates a PDF with:
      - Title at top of first page
      - Metadata line (source, date, classification)
      - Each section as a formatted heading + content
      - Page numbers in footer

    Args:
        report_title: Title of the report.
        sections: Dict mapping section heading → section content.
        source_file: Original data source filename.
        generated_at: ISO timestamp of report generation.
        output_path: Full path where the PDF should be saved.

    Returns:
        The output_path.
    """
    _ensure_fonts()
    t = _load_template()
    pdf = _make_pdf()

    # Sanitize Unicode if using Helvetica fallback
    sections = _sanitize_sections(sections)
    if not _use_dejavu:
        report_title = _cleanse_text(report_title)
        source_file = _cleanse_text(source_file)
        generated_at = _cleanse_text(generated_at)

    # ── Title header ──
    _write_title_header(pdf, report_title, source_file, generated_at)

    # ── Section content ──
    section_names = list(sections.keys())

    for i, section_name in enumerate(section_names):
        content = sections.get(section_name, "")
        if not content.strip():
            continue

        # Determine heading level: if it looks like "1. Executive Summary" or "1), level 1
        # Otherwise default to level 2
        heading_level = _detect_heading_level(section_name)

        _write_heading(pdf, section_name, level=heading_level)

        # Write paragraphs
        paragraphs = content.split("\n")
        body_cfg = _cfg("content", "body_text")
        for para in paragraphs:
            para = para.strip()
            if not para:
                pdf.ln(body_cfg.get("paragraph_spacing_mm", 2))
                continue
            _write_text(
                pdf,
                para,
                style=body_cfg.get("style", ""),
                size=body_cfg.get("font_size", 10),
                color_name="black",
                line_h=body_cfg.get("line_height_mm", 5.5),
                align=body_cfg.get("align", "L"),
            )
            pdf.ln(1.5)

        # Section separator
        if i < len(section_names) - 1:
            sep_cfg = _cfg("content", "section_separator")
            _draw_separator(pdf, sep_cfg.get("line_width_mm", 0.3))
            pdf.ln(sep_cfg.get("y_padding_mm", 3))

    # ── Page numbering ──
    # Disable FPDF's auto_page_break while we stamp the footer so multi_cell()
    # can't accidentally create empty trailing pages. We'll re-enable it
    # after the loop. We also use cell() instead of multi_cell() and place
    # the footer safely above the bottom margin so it never collides with
    # the limit.
    margin_b = t["page"]["margin_bottom"]
    page_h   = t["page"]["height_mm"]
    ft_config = t.get("footer", {})
    ft_text   = ft_config.get("text", "Page {current} of {total}")

    pdf.set_auto_page_break(auto=False)
    try:
        total_pages = pdf.page_no()
        # Position from bottom: keep the baseline comfortably above the bottom
        # margin so the footer line never crosses into the auto-break zone.
        y_offset = max(ft_config.get("y_from_bottom_mm", 10), margin_b + 2)
        # Estimate footer height: cell height ~ 2x font size in mm
        footer_h_mm = ft_config.get("font_size", 8) * 0.45 + 2
        y_pos = page_h - y_offset

        for page_num in range(1, total_pages + 1):
            pdf.page = page_num
            pdf.set_y(y_pos)
            label = ft_text.replace("{current}", str(page_num)).replace("{total}", str(total_pages))
            _set_font(pdf, ft_config.get("style", "I"), ft_config.get("font_size", 8))
            pdf.set_text_color(*_color("grey"))
            # cell() is single-line; it won't trigger a page break and won't
            # quietly add an empty page even at the bottom of the document.
            pdf.cell(
                w=_content_width(),
                h=footer_h_mm,
                text=_sanitize(_strip_markdown(label)),
                align="C",
            )
    finally:
        # Always restore auto_page_break so subsequent writes behave normally.
        pdf.set_auto_page_break(auto=True, margin=margin_b)

    # ── Save ──
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pdf.output(output_path)
    return output_path


def _detect_heading_level(section_name: str) -> int:
    """
    Detect heading level from section name conventions.
    - Leading number like "1. " or "1) " → level 1
    - Leading number like "1.1 " → level 2
    - Otherwise → level 2
    """
    s = section_name.strip()
    if s and s[0].isdigit():
        # Check for patterns like "1.", "1)", "1.1", "1.2.3"
        import re
        m = re.match(r'^(\d+(?:\.\d+)*)', s)
        if m:
            num_parts = m.group(1).split(".")
            return min(len(num_parts), 3)
    return 2  # Default to level 2
