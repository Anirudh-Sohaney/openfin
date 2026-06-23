"""
data_access.py
Key objective: Load filtered-data JSON files from main/data/filtered-data/
and extract metrics, analysis summaries, and metadata.

Parses the output format produced by subAgent 1:
    {
        "source_file": "original.csv",
        "processed_at": "2025-01-01T00:00:00",
        "llm_analysis": { ... },
        "computed_metrics": { "metric_name": value, ... }
    }
"""
import os
import json
from typing import Dict, List, Optional, Any, Tuple

# ── Paths relative to project root ─────────────────
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
FILTERED_DIR = os.path.join(PROJECT_ROOT, "data", "filtered-data")

# Directory for generated report JSONs from subAgent2
REPORTS_DIR = os.path.join(PROJECT_ROOT, "Agent1", "base-gens")


def _ensure_dirs():
    """Ensure data and report directories exist."""
    os.makedirs(FILTERED_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)


def get_filtered_files() -> List[str]:
    """
    Return sorted list of JSON file paths in the filtered-data directory.
    """
    _ensure_dirs()
    files = []
    for fname in sorted(os.listdir(FILTERED_DIR)):
        if fname.endswith(".json"):
            fpath = os.path.join(FILTERED_DIR, fname)
            if os.path.isfile(fpath):
                files.append(fpath)
    return files


def load_filtered_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a single filtered-data JSON file.

    Returns:
        The full JSON payload dict, or None on failure.
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not load {file_path}: {e}")
        return None


def extract_metrics(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the computed_metrics dict from a filtered-data payload.

    Also adds metadata fields:
    - source_file: original file name
    - processed_at: timestamp of subAgent1 processing
    - analysis_summary: summary from LLM analysis
    - column_mappings: identified column mappings
    """
    metrics = dict(payload.get("computed_metrics", {}))
    metrics["_source_file"] = payload.get("source_file", "unknown")
    metrics["_processed_at"] = payload.get("processed_at", "")
    metrics["_analysis_summary"] = (
        payload.get("llm_analysis", {}).get("analysis_summary", "")
    )

    # Flatten column_mappings as _col_* for LLM context
    mappings = payload.get("llm_analysis", {}).get("column_mappings", {})
    if mappings:
        for key, val in mappings.items():
            if val and isinstance(val, str) and val.strip():
                metrics[f"_col_{key}"] = val

    return metrics


def load_all_metrics() -> List[Dict[str, Any]]:
    """
    Load all filtered-data files and return a list of metric dicts.

    Each dict contains all computed_metrics plus metadata fields.
    """
    _ensure_dirs()
    all_metrics = []
    for file_path in get_filtered_files():
        payload = load_filtered_file(file_path)
        if payload is not None:
            metrics = extract_metrics(payload)
            all_metrics.append(metrics)
    return all_metrics


def get_existing_reports() -> Dict[str, str]:
    """
    Scan the base-reports directory for already generated reports.

    Returns:
        Dict mapping report name → file path.
    """
    _ensure_dirs()
    existing = {}
    for fname in sorted(os.listdir(REPORTS_DIR)):
        if fname.endswith(".json"):
            # Report name is filename without extension
            report_name = os.path.splitext(fname)[0]
            fpath = os.path.join(REPORTS_DIR, fname)
            if os.path.isfile(fpath):
                existing[report_name] = fpath
    return existing


def load_existing_report(report_name: str) -> Optional[Dict[str, Any]]:
    """
    Load a previously generated report for comparison (to check if metrics changed).

    Returns:
        The report dict, or None.
    """
    existing = get_existing_reports()
    if report_name not in existing:
        return None
    try:
        with open(existing[report_name], "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_report(report_name: str, report_data: Dict[str, Any]) -> str:
    """
    Save a generated report to the base-reports directory.

    Returns:
        Path to the saved JSON file.
    """
    _ensure_dirs()
    # Sanitize report_name for filename
    safe_name = report_name.lower().replace(" ", "_").replace("/", "_")
    out_path = os.path.join(REPORTS_DIR, f"{safe_name}.json")
    with open(out_path, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    return out_path


def compare_metrics_for_report(
    report_name: str,
    current_metrics: Dict[str, Any],
    old_report: Dict[str, Any],
) -> bool:
    """
    Compare the metrics used in an old report with current metrics
    to determine if the report needs regeneration.

    Returns:
        True if metrics have changed (report should be regenerated).
    """
    # Reports are saved as {report_name: {section: content, _metrics_used: {...}}}
    report_data = old_report.get(report_name, old_report)
    old_metrics = report_data.get("_metrics_used", {})
    if not old_metrics:
        return True  # No previously tracked metrics, regenerate

    # Compare relevant metric values
    for key, old_val in old_metrics.items():
        if key.startswith("_"):
            continue
        new_val = current_metrics.get(key)
        # Simple comparison — if values differ significantly, regenerate
        try:
            if old_val is None and new_val is not None:
                return True
            if old_val is not None and new_val is None:
                return True
            if old_val is not None and new_val is not None:
                if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                    if old_val == 0 and new_val == 0:
                        continue
                    if old_val == 0 or new_val == 0:
                        return True
                    if abs(float(old_val) - float(new_val)) / max(abs(float(old_val)), abs(float(new_val))) > 0.01:
                        return True
                elif old_val != new_val:
                    return True
        except (TypeError, ValueError, ZeroDivisionError):
            return True

    return False
