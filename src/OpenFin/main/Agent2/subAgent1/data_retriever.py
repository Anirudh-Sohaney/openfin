import os
import json
import re
from typing import Dict, List, Any, Optional


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
FILTERED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "filtered-data")
BASE_REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports", "base-reports")
INSIGHTS_DIR = os.path.join(PROJECT_ROOT, "reports", "insights")
# Fallback: original JSON sources (still kept for backwards compatibility)
BASE_GENS_DIR = os.path.join(PROJECT_ROOT, "Agent1", "base-gens")
INSIGHT_GENS_DIR = os.path.join(PROJECT_ROOT, "Agent1", "insight-gens")

# ── Common section headings found in generated reports/insights ─────────
# These are used to parse headings from extracted PDF text.
_KNOWN_HEADINGS = [
    "executive summary", "data", "methodology", "analysis",
    "risk assessment", "recommendations", "conclusion",
    "current state", "market research", "gap analysis",
    "estimated impact", "introduction", "overview",
    "key findings", "financial highlights", "performance summary",
    "product performance", "customer concentration",
    "revenue distribution", "profitability analysis",
    "cost analysis", "expense breakdown", "growth analysis",
    "competitive analysis", "pricing strategy", "action plan",
]


# ── JSON file loading (for filtered-data / fallback) ────────────────────

def _load_json_files(directory: str) -> List[Dict]:
    results = []
    if not os.path.exists(directory):
        return results
    for fname in sorted(os.listdir(directory)):
        fpath = os.path.join(directory, fname)
        if not fname.endswith(".json") or not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
            results.append({"filename": fname, "filepath": fpath, "data": data})
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Warning: Could not load {fname}: {e}")
    return results


# ── PDF file loading (for base-reports / insights) ──────────────────────

def _load_pdf_files(directory: str) -> List[Dict]:
    """Load PDF files from a directory and extract their text content.

    Returns a list of dicts with filename, filepath, and extracted data
    (parsed sections). The structure mirrors what _load_json_files returns
    so the ranking/extraction pipeline can be reused.
    """
    results = []
    if not os.path.exists(directory):
        return results
    for fname in sorted(os.listdir(directory)):
        fpath = os.path.join(directory, fname)
        if not fname.endswith(".pdf") or not os.path.isfile(fpath):
            continue
        try:
            sections = _extract_pdf_text(fpath)
            if sections:
                results.append({
                    "filename": fname,
                    "filepath": fpath,
                    "data": sections,
                })
        except Exception as e:
            print(f"  Warning: Could not extract text from {fname}: {e}")
    return results


def _extract_pdf_text(pdf_path: str) -> Dict[str, str]:
    """Extract text from a PDF file using pypdf and parse into sections.

    Uses pypdf (v6.x compatible) to extract page text, then heuristically
    parses the raw text into a dict of {section_heading: section_content}.
    The report-level title is stored under the key "_report_title".

    Returns an empty dict on failure.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        print("  Warning: pypdf is required for PDF extraction. "
              "Install with: pip install pypdf")
        return {}

    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    except Exception as e:
        print(f"  Warning: Could not read PDF {pdf_path}: {e}")
        return {}

    return _parse_pdf_text_into_sections(full_text)


def _parse_pdf_text_into_sections(full_text: str) -> Dict[str, str]:
    """Parse raw PDF text into structured sections.

    Strategy:
    1. Split text into lines.
    2. Try to detect section headings heuristically.
    3. Group content under each heading.
    4. Detect and extract the report title from before the first
       real section heading.

    Returns a dict keyed by section heading (with "_report_title" for
    the overall report title) or an empty dict if nothing could be parsed.
    """
    lines = full_text.split("\n")
    lines = [l.strip() for l in lines if l.strip()]

    if not lines:
        return {}

    # Attempt to separate the report title from the body.
    # The title is typically one of the first few non-empty lines.
    # After the title there is often a separator line or metadata.
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        # Skip page numbers and very short fragments
        if line.startswith("Page ") or len(line) < 5:
            continue
        # The first substantial line is usually the report title
        # (most report titles are 10-80 chars)
        if len(line) >= 10 and not line.endswith("."):
            # Make sure this isn't actually a known section heading
            if line.lower() not in _KNOWN_HEADINGS:
                title = line
                body_start = i + 1
                break

    # Now parse the body into sections.
    sections: Dict[str, str] = {}
    current_heading = "_intro"
    current_content: List[str] = []

    def _is_heading(line: str) -> bool:
        """Heuristic: a line looks like a heading if it is:
        - Matches a known heading name (regardless of length)
        - Or is a Title Case phrase (5-80 chars)
        - Or is a numbered list item like "1. Recommendation"
        - Doesn't end with sentence-ending punctuation (.!?)
        - Isn't a page number or confidentiality marker
        """
        stripped = line.strip()
        if not stripped:
            return False
        # Skip page numbers, metadata lines, file references
        if stripped.startswith("Page ") or stripped.startswith("Confidential"):
            return False
        # Match known heading keywords first (even very short ones like "Data")
        if stripped.lower() in _KNOWN_HEADINGS:
            return True
        # Max length check
        if len(stripped) > 80:
            return False
        # Min length check - skip very short lines (unless they matched known headings above)
        if len(stripped) < 5:
            return False
        # Reject if it ends with sentence-ending punctuation
        if stripped[-1] in ".!?:":
            return False
        # Pattern: "Risk Assessment", "Executive Summary"
        if re.match(r"^[A-Z][a-zA-Z\s\-/]{3,}$", stripped):
            return True
        # Pattern: "1. Section" or "1) Section"
        if re.match(r"^\d+[\).]\s+[A-Z]", stripped):
            return True
        return False

    for line in lines[body_start:]:
        # Skip footer / page number lines
        if re.match(r"^Page \d+ of \d+$", line):
            continue
        if line.startswith("Confidential"):
            continue
        if len(line) < 3:
            continue

        if _is_heading(line):
            # Flush previous heading's content
            if current_content:
                sections[current_heading] = "\n".join(current_content)
            current_heading = line.strip()
            current_content = []
        else:
            current_content.append(line)

    # Flush last heading
    if current_content:
        sections[current_heading] = "\n".join(current_content)

    if title:
        sections["_report_title"] = title

    return sections if len(sections) > 1 else {}


# ── Keyword relevance ranking ──────────────────────────────────────────

def _keyword_match_text(text: str, keywords: List[str]) -> int:
    """Count how many times the keywords appear in a text string."""
    score = 0
    text_lower = text.lower()
    for kw in keywords:
        score += text_lower.count(kw.lower())
    return score


def _keyword_match(entry: Dict, keywords: List[str]) -> int:
    """Count keyword matches in a data entry (works with both JSON and PDF-sourced dicts)."""
    data = entry.get("data", {})
    if isinstance(data, dict):
        return _keyword_match_text(json.dumps(data), keywords)
    return _keyword_match_text(str(data), keywords)


def _rank_by_relevance(files: List[Dict], keywords: List[str]) -> List[Dict]:
    for entry in files:
        entry["_relevance"] = _keyword_match(entry, keywords)
    files.sort(key=lambda x: x["_relevance"], reverse=True)
    return files


# ── JSON-specific data extraction ───────────────────────────────────────

METRICS_CONTAINER_KEYS = ["_metrics_used", "computed_metrics", "metrics"]


def _find_metrics_container(data: Dict) -> Optional[Dict]:
    for key in METRICS_CONTAINER_KEYS:
        if key in data and isinstance(data[key], dict):
            return data[key]
    for value in data.values():
        if isinstance(value, dict):
            for key in METRICS_CONTAINER_KEYS:
                if key in value and isinstance(value[key], dict):
                    return value[key]
    return None


def _extract_specific_fields(metrics: Dict, required_fields: List[str]) -> Dict:
    extracted = {}
    for field in required_fields:
        if field in metrics:
            extracted[field] = metrics[field]
        else:
            extracted[field] = None
    return extracted


def _extract_json_sections(data: Dict, keywords: List[str]) -> List[Dict]:
    sections = []
    if not isinstance(data, dict):
        return sections
    for key, value in data.items():
        key_lower = key.lower().replace(" ", "_")
        text = str(value).lower()
        if any(kw.lower() in key_lower or kw.lower() in text for kw in keywords):
            sections.append({"heading": key, "content": str(value)[:2000]})
    return sections


# ── PDF-specific data extraction ────────────────────────────────────────

def _extract_pdf_relevant_data(pdf_data: Dict, keywords: List[str]) -> Dict:
    """Extract relevant data from PDF-parsed sections.

    Returns the same structure as _extract_relevant_data for JSON, but without
    structured metrics (since PDFs don't have them).
    """
    result = {
        "source": pdf_data.get("filename", "unknown.pdf"),
        "source_type": "pdf_report",
        "metrics": {},
        "specific_fields": {},
        "content": {},
        "relevant_sections": [],
    }

    data = pdf_data.get("data", {})

    # Try to extract metrics from the text by searching for known field names
    # (e.g., "total_revenue", "gross_profit", etc.)
    full_text = "\n".join(
        str(v) for v in data.values() if isinstance(v, str) and not v.startswith("_")
    )
    result["content"] = data

    # Search for keyword-relevant sections
    for heading, content in data.items():
        if heading.startswith("_"):
            continue
        if any(kw.lower() in heading.lower() or kw.lower() in content.lower()
               for kw in keywords):
            result["relevant_sections"].append({
                "heading": heading,
                "content": content[:2000],
            })

    return result


# ── Source-specific loaders ─────────────────────────────────────────────

def _extract_relevant_data(file_data: Dict, keywords: List[str],
                          required_fields: Optional[List[str]] = None) -> Dict:
    """Extract relevant data from a file entry (JSON or PDF)."""
    data = file_data["data"]
    result = {
        "source": file_data["filename"],
        "source_type": "unknown",
        "metrics": {},
        "specific_fields": {},
        "content": "",
        "relevant_sections": [],
    }

    if isinstance(data, dict):
        # Check if this looks like PDF-parsed data (lacks deep nesting, has flat sections)
        has_report_title = "_report_title" in data
        is_likely_pdf = has_report_title or all(
            isinstance(v, str) for v in data.values()
        )

        if is_likely_pdf and not _find_metrics_container(data):
            # PDF-parsed data — extract as flat sections
            result["source_type"] = "pdf_report"
            result["content"] = data
            for heading, content in data.items():
                if heading.startswith("_"):
                    continue
                if any(kw.lower() in heading.lower() or kw.lower() in content.lower()
                       for kw in keywords):
                    result["relevant_sections"].append({
                        "heading": heading,
                        "content": content[:2000],
                    })
        else:
            # JSON-based data with nested structure
            metrics_container = _find_metrics_container(data)
            if metrics_container is not None:
                result["metrics"] = metrics_container
                if required_fields:
                    result["specific_fields"] = _extract_specific_fields(
                        metrics_container, required_fields
                    )

            for key, value in data.items():
                if isinstance(value, dict) and key not in METRICS_CONTAINER_KEYS:
                    result["source_type"] = key
                    result["content"] = value
                    result["relevant_sections"] = _extract_json_sections(value, keywords)
                    break
            else:
                result["content"] = data
                result["relevant_sections"] = _extract_json_sections(data, keywords)

    return result


def _load_filtered_data(keywords: List[str],
                        required_fields: Optional[List[str]] = None) -> Optional[Dict]:
    files = _load_json_files(FILTERED_DATA_DIR)
    if not files:
        return None

    ranked = _rank_by_relevance(files, keywords)
    if ranked and ranked[0]["_relevance"] > 0:
        return _extract_relevant_data(ranked[0], keywords, required_fields)

    combined = {
        "source": "all_filtered_data",
        "source_type": "combined_filtered_data",
        "metrics": {},
        "specific_fields": {},
        "content": {},
        "relevant_sections": [],
    }
    for entry in ranked:
        section = _extract_relevant_data(entry, keywords, required_fields)
        if section["metrics"]:
            combined["metrics"].update(section["metrics"])
        if section["specific_fields"]:
            combined["specific_fields"].update(section["specific_fields"])
        if section["content"]:
            combined["content"][entry["filename"]] = section["content"]
    return combined


def _load_base_reports(keywords: List[str]) -> Optional[Dict]:
    """Load base reports from PDF files in main/reports/base-reports/."""
    files = _load_pdf_files(BASE_REPORTS_DIR)

    # Fallback: also check JSON source files in base-gens/
    if not files:
        json_files = _load_json_files(BASE_GENS_DIR)
        if json_files:
            ranked = _rank_by_relevance(json_files, keywords)
            if ranked:
                return _extract_relevant_data(ranked[0], keywords)

    if not files:
        return None

    ranked = _rank_by_relevance(files, keywords)
    if ranked:
        return _extract_relevant_data(ranked[0], keywords)
    return None


def _load_insights(keywords: List[str]) -> Optional[Dict]:
    """Load insight reports from PDF files in main/reports/insights/."""
    files = _load_pdf_files(INSIGHTS_DIR)

    # Fallback: also check JSON source files in insight-gens/
    if not files:
        json_files = _load_json_files(INSIGHT_GENS_DIR)
        if json_files:
            ranked = _rank_by_relevance(json_files, keywords)
            if ranked:
                return _extract_relevant_data(ranked[0], keywords)

    if not files:
        return None

    ranked = _rank_by_relevance(files, keywords)
    if ranked:
        return _extract_relevant_data(ranked[0], keywords)
    return None


def _search_internet(query: str) -> Optional[Dict]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY is not set. Please configure your Tavily API key "
            "in the Config page."
        )

    try:
        from tavily import TavilyClient
    except ImportError:
        raise ImportError(
            "tavily package is required for internet search. "
            "Install with: pip install tavily"
        )

    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, search_depth="basic", max_results=5)

    results = []
    for r in response.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        })

    return {
        "source": "internet_search",
        "source_type": "tavily",
        "query": query,
        "results": results,
        "content": None,
        "metrics": {},
        "relevant_sections": results,
    }


def retrieve_data(analysis: Dict) -> Dict:
    data_source = analysis.get("data_source", "filtered-data")
    keywords = analysis.get("data_keywords", [])
    required_fields = analysis.get("required_data_fields", [])
    tavily_query = analysis.get("tavily_query")

    if data_source == "filtered-data":
        result = _load_filtered_data(keywords, required_fields)
        if result:
            return result

    if data_source == "base-reports":
        result = _load_base_reports(keywords)
        if result:
            return result

    if data_source == "insights":
        result = _load_insights(keywords)
        if result:
            return result

    if data_source == "internet" and tavily_query:
        return _search_internet(tavily_query)

    # Fallback through all sources
    fallback = _load_filtered_data(keywords, required_fields)
    if fallback:
        return fallback
    fallback = _load_base_reports(keywords)
    if fallback:
        return fallback
    fallback = _load_insights(keywords)
    if fallback:
        return fallback

    return {
        "source": "none",
        "source_type": "no_data_found",
        "metrics": {},
        "specific_fields": {},
        "content": "No relevant data found for the given prompt.",
        "relevant_sections": [],
    }
