import os
import json
from typing import Dict, List, Optional, Any, Tuple, Set

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
BASE_GENS_DIR = os.path.join(PROJECT_ROOT, "Agent1", "base-gens")
INSIGHT_GENS_DIR = os.path.join(PROJECT_ROOT, "Agent1", "insight-gens")
BASE_REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports", "base-reports")
INSIGHTS_DIR = os.path.join(PROJECT_ROOT, "reports", "insights")


def _ensure_dirs():
    os.makedirs(BASE_GENS_DIR, exist_ok=True)
    os.makedirs(INSIGHT_GENS_DIR, exist_ok=True)
    os.makedirs(BASE_REPORTS_DIR, exist_ok=True)
    os.makedirs(INSIGHTS_DIR, exist_ok=True)


def _scan_json_files(directory: str) -> Dict[str, str]:
    _ensure_dirs()
    files = {}
    if not os.path.isdir(directory):
        return files
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".json"):
            base = os.path.splitext(fname)[0]
            fpath = os.path.join(directory, fname)
            if os.path.isfile(fpath):
                files[base] = fpath
    return files


def get_json_report_files() -> Dict[str, str]:
    return _scan_json_files(BASE_GENS_DIR)


def get_json_insight_files() -> Dict[str, str]:
    return _scan_json_files(INSIGHT_GENS_DIR)


def get_existing_pdf_files(directory: str) -> Set[str]:
    existing = set()
    if not os.path.isdir(directory):
        return existing
    for fname in os.listdir(directory):
        if fname.endswith(".pdf"):
            existing.add(os.path.splitext(fname)[0])
    return existing


def load_report_file(file_path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not load {file_path}: {e}")
        return None


def extract_report_sections(
    data: Dict[str, Any],
) -> Tuple[str, Dict[str, str], str, str]:
    report_title = ""
    sections = {}
    source_file = ""
    generated_at = ""

    for key, val in data.items():
        if isinstance(val, dict):
            report_title = key
            for section_key, section_val in val.items():
                if section_key.startswith("_"):
                    if section_key == "_source_file":
                        source_file = str(section_val) if section_val else ""
                    elif section_key == "_generated_at":
                        generated_at = str(section_val) if section_val else ""
                else:
                    sections[section_key] = _value_to_text(section_val)
            break

    return report_title, sections, source_file, generated_at


def _value_to_text(val: Any) -> str:
    if isinstance(val, str):
        return val
    if isinstance(val, (int, float, bool)):
        return str(val)
    if isinstance(val, list):
        return "\n".join(_value_to_text(item) for item in val)
    if isinstance(val, dict):
        lines = []
        for k, v in val.items():
            if not k.startswith("_"):
                lines.append(f"{k}: {_value_to_text(v)}")
        return "\n".join(lines)
    return str(val)


def pdf_output_path_for(source_category: str, basename: str) -> str:
    if source_category == "base-report":
        return os.path.join(BASE_REPORTS_DIR, f"{basename}.pdf")
    elif source_category == "insight":
        return os.path.join(INSIGHTS_DIR, f"{basename}.pdf")
    return os.path.join(BASE_REPORTS_DIR, f"{basename}.pdf")
