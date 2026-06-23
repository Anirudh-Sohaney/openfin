import os
import json
import time
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, List

from .data_loader import load_and_prepare
from .llm_interface import analyze_dataframe
from .metrics_calculator import calculate_metrics
from .data_allocator import allocate_and_merge, get_output_filename

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "uploaded-data")
FILTERED_DIR = os.path.join(PROJECT_ROOT, "data", "filtered-data")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")


def _ensure_dirs():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(FILTERED_DIR, exist_ok=True)


def _set_activity(status: str):
    with open(LOG_FILE, "w") as f:
        f.write(status.strip() + "\n")


def _get_pending_files() -> List[str]:
    _ensure_dirs()
    files = []
    for fname in sorted(os.listdir(UPLOAD_DIR)):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath):
            files.append(fpath)
    return files


def _save_results(
    original_filename: str,
    analysis: Dict[str, Any],
    metrics: Dict[str, Any],
) -> str:
    _ensure_dirs()
    payload = allocate_and_merge(
        new_source_filename=original_filename,
        new_analysis=analysis,
        new_metrics=metrics,
        filtered_dir=FILTERED_DIR,
    )
    base_name = payload.get("base_name", os.path.splitext(original_filename)[0])
    output_filename = get_output_filename(base_name)
    out_path = os.path.join(FILTERED_DIR, output_filename)

    is_merged = payload.pop("is_merged", False)
    merged_from = payload.pop("merged_from", None)
    merge_period = payload.pop("merge_period", None)
    payload.pop("base_name", None)

    if is_merged:
        payload["allocation"] = {
            "merged_from": merged_from,
            "merge_period": merge_period,
        }

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return out_path


def _delete_source(file_path: str):
    try:
        os.remove(file_path)
    except OSError as e:
        print(f"Warning: could not delete {file_path}: {e}")


def process_file(file_path: str) -> Optional[str]:
    filename = os.path.basename(file_path)
    _set_activity("breaking down data")
    start_time = time.time()

    try:
        df, date_col = load_and_prepare(file_path)

        if df.empty:
            print(f"FAILED: empty DataFrame for {filename}")
            _set_activity("idle")
            return None

        print(f"Loaded {len(df)} rows x {len(df.columns)} cols, date_col={date_col}")

        analysis = analyze_dataframe(df, date_col)

        derivable = analysis.get("derivable_metrics", [])
        timeframes = analysis.get("timeframe_available", [])
        mappings = analysis.get("column_mappings", {})
        summary = analysis.get("analysis_summary", "")

        print(f"Analysis complete: {len(derivable)} derivable metrics, "
              f"timeframes={timeframes}")

        metrics = calculate_metrics(df, date_col, mappings, derivable, timeframes)
        print(f"Computed {len(metrics)} metric values")

        out_path = _save_results(filename, analysis, metrics)
        print(f"Saved filtered data to {os.path.basename(out_path)}")

        _delete_source(file_path)

        elapsed = time.time() - start_time
        print(f"Completed {filename}: {elapsed:.1f}s, {len(metrics)} metrics")

        _set_activity("idle")
        return out_path

    except Exception as e:
        print(f"ERROR processing {filename}: {e}")
        import traceback
        traceback.print_exc()
        _set_activity("idle")
        return None


def process_all() -> Dict[str, Optional[str]]:
    _ensure_dirs()
    results = {}
    pending = _get_pending_files()

    if not pending:
        print("No files found in upload directory.")
        return results

    for file_path in pending:
        out_path = process_file(file_path)
        results[os.path.basename(file_path)] = out_path

    return results


def run() -> Dict[str, Optional[str]]:
    return process_all()


def test():
    test_data = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=12, freq="ME"),
        "revenue": [10000, 12000, 11000, 13000, 14000, 12500,
                    15000, 16000, 14500, 17000, 18000, 19000],
        "units_sold": [100, 110, 105, 120, 130, 115,
                       140, 150, 135, 155, 165, 175],
        "expenses": [7000, 8000, 7500, 8500, 9000, 8200,
                     9500, 10000, 9200, 10500, 11000, 11500],
    })

    print("=" * 60)
    print("subAgent 1 — TEST MODE (inline data, no file I/O)")
    print("=" * 60)

    _set_activity("breaking down data")

    print(f"\nTest DataFrame: {len(test_data)} rows x {len(test_data.columns)} cols")

    date_col = "date"
    analysis = analyze_dataframe(test_data, date_col)
    derivable = analysis.get("derivable_metrics", [])
    timeframes = analysis.get("timeframe_available", [])
    mappings = analysis.get("column_mappings", {})

    print(f"Column mappings: {json.dumps(mappings, indent=2)}")
    print(f"Derivable metrics ({len(derivable)}): {derivable}")
    print(f"Timeframes: {timeframes}")

    metrics = calculate_metrics(test_data, date_col, mappings, derivable, timeframes)

    print(f"\nComputed metrics ({len(metrics)}):")
    for key, val in sorted(metrics.items()):
        if isinstance(val, float):
            print(f"  {key}: {val:.2f}")
        elif isinstance(val, dict):
            print(f"  {key}: {{... {len(val)} entries}}")
        elif isinstance(val, list):
            print(f"  {key}: [... {len(val)} items]")
        else:
            print(f"  {key}: {val}")

    _set_activity("idle")
    print("\nsubAgent 1 — TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        test()
    else:
        results = run()
        if results:
            print(f"\nProcessed {len(results)} file(s):")
            for fname, out in results.items():
                status = "OK -> " + os.path.basename(out) if out else "FAILED"
                print(f"  {fname}: {status}")
        else:
            print("No files to process.")
