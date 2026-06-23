"""
data_allocator.py
Key objective: Properly allocate new derived metrics against existing filtered data.
When a new dataset arrives (e.g., revenue_2026.csv after revenue_2025.csv was processed):

- SNAPSHOT metrics (point-in-time values like total_revenue, net_profit, customer_count):
    Replaced with new data values — the latest data represents the current state.
- TREND metrics (growth rates, volatility, scores, ratios computed over time):
    Preserved in a history dictionary keyed by processing period, so larger-timeframe
    trend data from older datasets is retained alongside new trend data.
- LIST metrics (time-series like monthly_revenue_list, quarterly_revenue_list):
    Merged by appending new entries to the existing list.

The module also handles filename normalization to detect related datasets
(e.g., "revenue_2025.csv" and "revenue_2026.csv" both map to "revenue_filtered.json").
"""
import os
import re
import json
from typing import Dict, Any, Optional, List, Tuple, Tuple


# ── Metric categorization ──────────────────────────────────────────

# Keywords that identify TREND metrics (preserve history across datasets).
# These represent trends, rates, or larger-timeframe derived values that should
# accumulate history rather than being replaced by the latest snapshot.
TREND_KEYWORDS = [
    "growth", "rate", "roi", "volatility", "compression",
    "score", "turnover", "runway", "lifetime",
    "forecast", "break_even", "period", "retention",
    "repeat_purchase",
]

# Note: "rate" is a substring keyword (not regex) because:
# - "rate" is NOT a substring of "ratio" (r-a-t-e vs r-a-t-i-o), so no false positive.
# - Word-boundary regex (\b) doesn't work after underscore since _ is \w.


def _normalize_filename(filename: str) -> str:
    """
    Normalize a filename by stripping date/year patterns, numbers, and extensions
    to extract the base category name.

    Examples:
        revenue_2025.csv → revenue
        revenue_2026.csv → revenue
        sales.csv → sales
        expenses_2024.csv → expenses
        Q1-2025_revenue.xlsx → revenue
    """
    base = os.path.splitext(filename)[0]  # Remove extension
    # Remove year patterns: YYYY, YYYY-YYYY, YYYY_YYYY
    base = re.sub(r'_?(\d{4})([-_]\d{4})?$', '', base)
    # Remove date prefixes like Q1-2025_, Q2-2024_
    base = re.sub(r'^(FY|Q\d)[-_\d]+[-_]', '', base)
    # Remove trailing numbers/underscores
    base = re.sub(r'[\d_]+$', '', base)
    # Clean up extra underscores/dashes
    base = re.sub(r'[_-]+$', '', base)
    base = re.sub(r'^[_-]+', '', base)
    return base.lower().strip()


def _find_existing_filtered(base_name: str, filtered_dir: str) -> Optional[str]:
    """
    Find an existing filtered JSON file that matches the normalized base name.

    Returns the full path to the existing file, or None if no match found.
    """
    target_filename = f"{base_name}_filtered.json"
    candidate_path = os.path.join(filtered_dir, target_filename)
    if os.path.isfile(candidate_path):
        return candidate_path

    # Fallback: fuzzy match by checking all filtered files
    try:
        for fname in os.listdir(filtered_dir):
            if not fname.endswith("_filtered.json"):
                continue
            fbase = fname.replace("_filtered.json", "")
            # Check if one base name contains the other
            if base_name in fbase or fbase in base_name:
                return os.path.join(filtered_dir, fname)
    except OSError:
        pass

    return None


def _is_period_dict(d: dict) -> bool:
    """
    Check if a dict looks like a trend-history dict (keyed by period IDs)
    rather than an entity-keyed dict (product/customer names).

    Period keys are: 4-digit years (e.g. "2025"), "historical",
    or timeframe strings like "12_months".
    """
    if not d:
        return False
    period_pattern = re.compile(r'^(\d{4}|historical|\d+_months|latest)$')
    return all(period_pattern.match(str(k)) for k in d.keys())


def _unwrap_history_dict(old_val) -> Tuple[dict, bool]:
    """
    Given an old TREND value, extract the flat history dict and whether
    the value was already a history dict.

    Returns (history_dict, was_already_history).

    Handles nesting: if the old value is {"historical": {"historical": 0.15, "2026": 0.12}},
    unwrap to the inner history dict.
    """
    if isinstance(old_val, dict):
        # Check if it's already a proper history dict (period-keyed)
        if _is_period_dict(old_val):
            return dict(old_val), True
        # Check if it's wrapped: {"historical": inner_dict}
        if "historical" in old_val and len(old_val) == 1:
            inner = old_val["historical"]
            if isinstance(inner, dict):
                # Recurse to unwrap further nesting
                return _unwrap_history_dict(inner)
            else:
                return {"historical": inner}, True
        # It's an entity-keyed dict (product/customer names) — wrap it
        return {"historical": old_val}, True
    elif old_val is not None:
        # Scalar value — wrap as historical
        return {"historical": old_val}, False
    else:
        return {}, False


def categorize_metric(metric_name: str) -> str:
    """
    Categorize a metric as SNAPSHOT, TREND, or LIST.

    LIST:    metric name ends with '_list' (time-series arrays)
    TREND:   metric name contains trend-related keywords (growth, roi, volatility, etc.)
             with word-boundary matching for ambiguous keywords like "rate".
    SNAPSHOT: everything else (point-in-time values)
    """
    if metric_name.endswith("_list"):
        return "LIST"

    name_lower = metric_name.lower()

    # Check substring keywords
    for keyword in TREND_KEYWORDS:
        if keyword in name_lower:
            return "TREND"

    return "SNAPSHOT"


def _extract_period_id(
    new_analysis: Dict[str, Any],
    filename: str,
) -> str:
    """
    Extract a period identifier from the new dataset for use as a key
    in trend history dictionaries.

    Tries to extract a year or date from the filename, or falls back
    to the processing timestamp.
    """
    # Try to extract year from filename
    year_match = re.search(r'(\d{4})', filename)
    if year_match:
        return year_match.group(1)

    # Fall back to timeframe in analysis
    timeframes = new_analysis.get("timeframe_available", [])
    if timeframes:
        return timeframes[-1]  # e.g., "12_months"

    return "latest"


def merge_metrics(
    old_metrics: Dict[str, Any],
    new_metrics: Dict[str, Any],
    period_id: str = "latest",
) -> Dict[str, Any]:
    """
    Merge newly computed metrics into existing (old) metrics with proper allocation.

    Allocation rules:
    - SNAPSHOT: replace old value with new value
    - TREND: preserve history. Old value stored under a 'historical' key or date-keyed
      dict; new value added with period_id as key.
    - LIST: append new list entries to old list entries.

    Parameters
    ----------
    old_metrics : dict
        Previously stored computed_metrics from an existing filtered JSON file.
    new_metrics : dict
        Newly computed metrics from the current dataset.
    period_id : str
        Identifier for the new data period (e.g., "2026").

    Returns
    -------
    dict
        Merged metrics dictionary.
    """
    merged = {}

    # Collect all unique keys from both old and new
    all_keys = set(old_metrics.keys()) | set(new_metrics.keys())

    for key in all_keys:
        cat = categorize_metric(key)
        old_val = old_metrics.get(key)
        new_val = new_metrics.get(key)

        if cat == "SNAPSHOT":
            # Replace with new value; fall back to old if new is None/missing
            if new_val is not None:
                merged[key] = new_val
            elif old_val is not None:
                merged[key] = old_val
            # else: omit (both None)

        elif cat == "LIST":
            # Append new list entries to old list
            old_list = old_val if isinstance(old_val, list) else []
            new_list = new_val if isinstance(new_val, list) else []
            merged[key] = old_list + new_list

        elif cat == "TREND":
            # Preserve history in a dictionary keyed by period.
            # Uses _unwrap_history_dict to safely extract prior history,
            # handling scalar values, period-keyed dicts, wrapped {"historical": ...}
            # dicts, and entity-keyed dicts (product/customer names).
            history, _ = _unwrap_history_dict(old_val)

            if new_val is not None:
                history[period_id] = new_val

            if history:
                merged[key] = history

    return merged


def merge_analysis(
    old_analysis: Dict[str, Any],
    new_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge LLM analysis data: combine derivable metrics, timeframes, and
    update column mappings and summary.

    The new analysis takes precedence for column_mappings, but
    derivable_metrics and timeframes are unioned.
    """
    merged = {}

    # Column mappings: new data defines the mapping (most recent column structure)
    merged["column_mappings"] = new_analysis.get("column_mappings", old_analysis.get("column_mappings", {}))

    # Derivable metrics: union of old and new
    old_derivable = set(old_analysis.get("derivable_metrics", []))
    new_derivable = set(new_analysis.get("derivable_metrics", []))
    merged["derivable_metrics"] = sorted(old_derivable | new_derivable)

    # Timeframes: union of old and new
    old_tf = set(old_analysis.get("timeframe_available", []))
    new_tf = set(new_analysis.get("timeframe_available", []))
    merged["timeframe_available"] = sorted(old_tf | new_tf)

    # Analysis summary: concatenate
    merged["analysis_summary"] = (
        f"[Previous] {old_analysis.get('analysis_summary', '')}\n"
        f"[Latest] {new_analysis.get('analysis_summary', '')}"
    )

    return merged


def merge_source_files(old_source: str, new_source: str) -> str:
    """
    Combine source file references, tracking history.
    """
    if old_source and old_source != new_source:
        return f"{new_source} (previous: {old_source})"
    return new_source


def allocate_and_merge(
    new_source_filename: str,
    new_analysis: Dict[str, Any],
    new_metrics: Dict[str, Any],
    filtered_dir: str,
) -> Dict[str, Any]:
    """
    Main entry point for data allocation.

    Determines if existing filtered data exists for the same category,
    merges if so, and returns the final payload to be saved.

    Parameters
    ----------
    new_source_filename : str
        Name of the newly processed source file (e.g., "revenue_2026.csv").
    new_analysis : dict
        LLM analysis result from the new dataset.
    new_metrics : dict
        Computed metrics from the new dataset.
    filtered_dir : str
        Path to the filtered-data directory.

    Returns
    -------
    dict
        The complete payload to save, with:
        - source_file: merged source references
        - processed_at: current timestamp
        - llm_analysis: merged analysis
        - computed_metrics: merged metrics with proper allocation
        Also includes:
        - is_merged: bool indicating if data was merged
        - base_name: the normalized base name used for matching
    """
    from datetime import datetime

    base_name = _normalize_filename(new_source_filename)
    existing_path = _find_existing_filtered(base_name, filtered_dir)

    if existing_path is None:
        # No existing data — return new payload as-is
        return {
            "source_file": new_source_filename,
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            "llm_analysis": new_analysis,
            "computed_metrics": new_metrics,
            "is_merged": False,
            "base_name": base_name,
        }

    # Load existing filtered data
    try:
        with open(existing_path, "r") as f:
            existing_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Warning: could not read existing filtered data ({e}), saving as new.")
        return {
            "source_file": new_source_filename,
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            "llm_analysis": new_analysis,
            "computed_metrics": new_metrics,
            "is_merged": False,
            "base_name": base_name,
        }

    period_id = _extract_period_id(new_analysis, new_source_filename)

    # Merge each section
    old_analysis = existing_data.get("llm_analysis", {})
    old_metrics = existing_data.get("computed_metrics", {})
    old_source = existing_data.get("source_file", "")

    merged_analysis = merge_analysis(old_analysis, new_analysis)
    merged_metrics = merge_metrics(old_metrics, new_metrics, period_id)
    merged_source = merge_source_files(old_source, new_source_filename)

    return {
        "source_file": merged_source,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "llm_analysis": merged_analysis,
        "computed_metrics": merged_metrics,
        "is_merged": True,
        "base_name": base_name,
        "merged_from": os.path.basename(existing_path),
        "merge_period": period_id,
    }


def get_output_filename(base_name: str) -> str:
    """
    Get the standardized output filename for a given base name.

    Example: get_output_filename("revenue") → "revenue_filtered.json"
    """
    return f"{base_name}_filtered.json"
