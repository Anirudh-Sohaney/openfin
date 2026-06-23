"""
data_access.py
Key objective: Load filtered-data JSON files from main/data/filtered-data/
and extract metrics, analysis summaries, and metadata for subAgent3 research.

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
from typing import Dict, List, Optional, Any

# ── Paths relative to project root ─────────────────
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
FILTERED_DIR = os.path.join(PROJECT_ROOT, "data", "filtered-data")

# Directory for research insight JSONs (specs: saves to main/Agent1/insight-gens)
INSIGHTS_DIR = os.path.join(PROJECT_ROOT, "Agent1", "insight-gens")


def _ensure_dirs():
    """Ensure data and insights directories exist."""
    os.makedirs(FILTERED_DIR, exist_ok=True)
    os.makedirs(INSIGHTS_DIR, exist_ok=True)


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
    Extract the computed_metrics dict from a filtered-data payload and
    add metadata tags. Reuses the same extraction logic as subAgent 2.
    """
    metrics = dict(payload.get("computed_metrics", {}))
    metrics["_source_file"] = payload.get("source_file", "unknown")
    metrics["_processed_at"] = payload.get("processed_at", "")
    metrics["_analysis_summary"] = (
        payload.get("llm_analysis", {}).get("analysis_summary", "")
    )
    # Flatten column_mappings for LLM context
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
            all_metrics.append(extract_metrics(payload))
    return all_metrics


def get_existing_insight_files() -> set:
    """
    Return a set of existing insight report filenames (without .json extension).
    Used to avoid regenerating reports that already exist.
    """
    _ensure_dirs()
    existing = set()
    for fname in os.listdir(INSIGHTS_DIR):
        if fname.endswith(".json"):
            base = fname[:-5]  # strip .json
            existing.add(base)
    return existing


def topic_to_insight_filename(topic: str) -> str:
    """
    Convert a research topic identifier to the expected insight filename (without extension).

    E.g. "pricing_optimization_opportunities" -> "pricing_optimization_opportunities_research"
    """
    return f"{topic}_research"


def save_insight(report_name: str, report_data: Dict[str, Any]) -> str:
    """
    Save a research insight report to the insights directory.

    Returns:
        Path to the saved JSON file.
    """
    _ensure_dirs()
    safe_name = report_name.lower().replace(" ", "_").replace("/", "_")
    out_path = os.path.join(INSIGHTS_DIR, f"{safe_name}.json")
    with open(out_path, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    return out_path
