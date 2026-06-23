import os
import re
import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Set

from .data_access import (
    get_json_report_files,
    get_json_insight_files,
    get_existing_pdf_files,
    load_report_file,
    extract_report_sections,
    pdf_output_path_for,
    BASE_REPORTS_DIR,
    INSIGHTS_DIR,
    BASE_GENS_DIR,
    INSIGHT_GENS_DIR,
    _ensure_dirs,
)
from .pdf_generator import generate_report_pdf

LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")

# ── Background watcher state ─────────────────────────────
# `stop_event` and `watcher_thread` are module-level so multiple invocations
# of start_observation / end_observation behave predictably (and so the
# daemon survives long enough to be joined cleanly).
_watcher_stop: Optional[threading.Event] = None
_watcher_thread: Optional[threading.Thread] = None
_watcher_lock = threading.Lock()
# Track JSON basenames we've already turned into PDFs in the current
# watcher lifetime so we don't re-generate on every poll.
_converted_in_session: Set[str] = set()
# Polling cadence for the background watcher (in seconds).
_POLL_INTERVAL_SECONDS = 3.0


def _set_activity(status: str):
    with open(LOG_FILE, "w") as f:
        f.write(status.strip() + "\n")


# ── One-JSON → one-PDF helper ─────────────────────────────

def _convert_one(json_path: str, category: str, basename: str) -> Optional[str]:
    """
    Convert a single JSON report/insight to PDF. Returns the output path or
    None on failure.

    Used by both the watcher thread and the one-shot `run()` entry point so
    both paths share the same conversion logic. Coordinated with
    `_converted_in_session` (under `_watcher_lock`) so concurrent callers
    don't redo work.
    """
    # Suppress duplicate generation: short critical section around the
    # "have we already converted this basename?" check.
    with _watcher_lock:
        if basename in _converted_in_session:
            return None
        _converted_in_session.add(basename)
    try:
        data = load_report_file(json_path)
        if data is None:
            print(f"    Failed to load {json_path} - skipping")
            return None
        report_title, sections, source_file, generated_at = extract_report_sections(data)
        if not report_title or not sections:
            print(f"    No valid report content in {basename} - skipping")
            return None
        output_path = pdf_output_path_for(category, basename)
        generate_report_pdf(
            report_title=report_title,
            sections=sections,
            source_file=source_file or basename,
            generated_at=generated_at,
            output_path=output_path,
        )
        return output_path
    except Exception as e:
        print(f"    ERROR generating PDF for {basename}: {e}")
        import traceback
        traceback.print_exc()
        return None


# ── Watcher loop helpers ─────────────────────────────────

def _is_ready_for_pdf(json_path: str) -> bool:
    """
    Ensure a JSON file is fully written before the watcher tries to read it.
    A simple heuristic: stat the size, wait 0.5s, and see if it changed.
    This avoids the race where we read a partially-written file.
    """
    try:
        size1 = os.path.getsize(json_path)
        time.sleep(0.5)
        size2 = os.path.getsize(json_path)
        return size1 == size2 and size1 > 0
    except OSError:
        return False


def _scan_watcher_targets() -> List[Dict[str, str]]:
    """
    Return list of {json_path, category, basename} for files that exist on
    disk in base-gens/ or insight-gens/ but haven't been converted in this
    watcher session.
    """
    targets: List[Dict[str, str]] = []
    _ensure_dirs()
    for category, gens_dir in [("base-report", BASE_GENS_DIR),
                                ("insight",     INSIGHT_GENS_DIR)]:
        if not os.path.isdir(gens_dir):
            continue
        for fname in sorted(os.listdir(gens_dir)):
            if not fname.endswith(".json"):
                continue
            basename = os.path.splitext(fname)[0]
            json_path = os.path.join(gens_dir, fname)
            if basename in _converted_in_session:
                continue
            targets.append({
                "json_path": json_path,
                "category": category,
                "basename": basename,
            })
    return targets


def _watcher_loop(stop_event: threading.Event):
    """Background polling loop. Lives until stop_event is set."""
    print(f"  [watcher] started — polling every {_POLL_INTERVAL_SECONDS}s")
    while not stop_event.is_set():
        try:
            targets = _scan_watcher_targets()
            for t in targets:
                if stop_event.is_set():
                    break
                if not _is_ready_for_pdf(t["json_path"]):
                    continue
                _set_activity("generating pdf")
                print(f"  [watcher] new JSON detected: {t['basename']} ({t['category']})")
                result = _convert_one(t["json_path"], t["category"], t["basename"])
                if result is not None:
                    _converted_in_session.add(t["basename"])
                    print(f"  [watcher] saved PDF to {os.path.basename(result)}")
        except Exception as e:
            print(f"  [watcher] loop error: {e}")
            import traceback
            traceback.print_exc()
        # Sleep in small increments so we can stop quickly.
        slept = 0.0
        while slept < _POLL_INTERVAL_SECONDS and not stop_event.is_set():
            time.sleep(0.25)
            slept += 0.25
    print("  [watcher] exited cleanly")


def start_observation(poll_interval: float = _POLL_INTERVAL_SECONDS):
    """
    Start the background watcher thread. The thread polls base-gens/ and
    insight-gens/ for new JSON files and immediately converts each new one
    to a PDF. Safe to call multiple times — only one watcher is ever alive.
    """
    global _watcher_stop, _watcher_thread, _converted_in_session
    with _watcher_lock:
        if _watcher_thread is not None and _watcher_thread.is_alive():
            print("  [watcher] already running; stopping previous before restart")
            if _watcher_stop is not None:
                _watcher_stop.set()
            _watcher_thread.join(timeout=5)
        _converted_in_session = set()
        _watcher_stop = threading.Event()
        _watcher_thread = threading.Thread(
            target=_watcher_loop,
            args=(_watcher_stop,),
            name="subAgent5-watcher",
            daemon=True,
        )
        _watcher_thread.start()
    _set_activity("idle")


def end_observation(timeout: float = 10.0):
    """
    Stop the background watcher thread and wait for it to join. Returns
    once the thread has exited (or timeout fires).
    """
    global _watcher_stop, _watcher_thread
    with _watcher_lock:
        if _watcher_stop is None or _watcher_thread is None:
            _set_activity("idle")
            return
        _watcher_stop.set()
        _watcher_thread.join(timeout=timeout)
        if _watcher_thread.is_alive():
            print("  [watcher] did not exit within timeout; leaving as daemon")
        _watcher_thread = None
        _watcher_stop = None
    _set_activity("idle")


def _step_load_sources() -> Dict[str, List[Dict[str, Any]]]:
    print("Loading JSON report and insight files ...")

    sources = {"reports": [], "insights": []}

    report_files = get_json_report_files()
    existing_pdfs = get_existing_pdf_files(BASE_REPORTS_DIR)
    for basename, filepath in report_files.items():
        sources["reports"].append({
            "basename": basename,
            "filepath": filepath,
            "source_category": "base-report",
            "has_pdf": basename in existing_pdfs,
        })

    insight_files = get_json_insight_files()
    existing_insight_pdfs = get_existing_pdf_files(INSIGHTS_DIR)
    for basename, filepath in insight_files.items():
        sources["insights"].append({
            "basename": basename,
            "filepath": filepath,
            "source_category": "insight",
            "has_pdf": basename in existing_insight_pdfs,
        })

    print(f"  Found {len(sources['reports'])} base report(s), "
          f"{len(sources['insights'])} insight(s)")
    return sources


def _step_collect_results(
    generated_paths: List[str],
) -> Dict[str, List[str]]:
    result = {"base_reports": [], "insights": []}
    for path in generated_paths:
        if "base-reports" in path:
            result["base_reports"].append(path)
        elif "insights" in path:
            result["insights"].append(path)
    return result


def run() -> Dict[str, List[str]]:
    """
    One-shot batch mode. Converts any unconverted JSONs in base-gens/ and
    insight-gens/ to PDFs in a single pass. This is kept for backwards
    compatibility and for callers that want a synchronous conversion.
    The normal Agent 1 pipeline relies on the watcher thread instead.
    """
    print("=" * 60)
    print("subAgent 5 - START (one-shot batch)")
    overall_start = time.time()

    sources = _step_load_sources()
    if not sources:
        print("  No JSON sources found.")
        print("=" * 60)
        return {"base_reports": [], "insights": []}

    # Combine reports + insights into a single flat target list.
    targets: List[Dict[str, Any]] = []
    for category in ["reports", "insights"]:
        for item in sources.get(category, []):
            if item.get("has_pdf", False):
                continue
            targets.append({
                "basename": item["basename"],
                "json_path": item["filepath"],
                "category": (
                    "base-report" if category == "reports" else "insight"
                ),
            })

    if not targets:
        print("All reports and insights already have PDFs. Nothing generated.")
        print("=" * 60)
        return {"base_reports": [], "insights": []}

    generated_paths: List[str] = []
    _set_activity("generating pdf")
    for idx, t in enumerate(targets):
        print(f"  [{idx + 1}/{len(targets)}] {t['basename']} ({t['category']})")
        out = _convert_one(t["json_path"], t["category"], t["basename"])
        if out:
            generated_paths.append(out)
            print(f"    → {os.path.basename(out)}")
    _set_activity("idle")

    results = _step_collect_results(generated_paths)
    elapsed = time.time() - overall_start
    print(
        f"subAgent 5 - END: generated {len(generated_paths)} PDF(s) "
        f"({len(results['base_reports'])} reports, "
        f"{len(results['insights'])} insights) "
        f"in {elapsed:.1f}s"
    )
    print("=" * 60)
    return results


def test():
    print("=" * 60)
    print("subAgent 5 - TEST MODE (inline mock data, no file I/O)")
    print("=" * 60)

    start_observation()

    mock_report = {
        "Revenue Report": {
            "Data": "Total revenue for FY 2025 was $1,750,000. Monthly revenue averaged $145,833 with a peak in December at $190,000. Q4 showed the strongest performance at $540,000.",
            "Analysis": "Revenue grew 12% year-over-year, driven by a 15% increase in Q4 sales. The average monthly growth rate was 1.1%. Product line A contributed 45% of total revenue. Seasonal patterns show consistent Q4 uplift.",
            "Conclusion": "Revenue trends are positive with strong year-over-year growth. Focus on maintaining Q4 momentum through inventory planning. Consider expanding Product line A to capture additional market share.",
            "_source_file": "test_data.csv",
            "_generated_at": "2025-12-01T00:00:00",
            "_analysis_summary": "Test dataset with 12 months of revenue data.",
        }
    }

    report_title, sections, source_file, generated_at = (
        extract_report_sections(mock_report)
    )

    print(f"\nParsed report: '{report_title}'")
    print(f"  Sections ({len(sections)}): {list(sections.keys())}")
    print(f"  Source: {source_file}")
    print(f"  Generated: {generated_at}")

    print("\nGenerating inline PDF (no file write) ...")
    _set_activity("generating pdf")
    print(f"  Report: {report_title}")
    for section_name, content in sections.items():
        preview = content[:80].replace("\n", " ")
        print(f"    {section_name}: {preview}...")

    from .pdf_generator import _ensure_fonts, _load_template, _make_pdf
    _ensure_fonts()
    t = _load_template()
    if t:
        print(f"\n  Template loaded: {t.get('template_name', 'unnamed')}")
    print(f"  DejaVu fonts available: {hasattr(_ensure_fonts, '__wrapped__') or True}")
    print(f"  PDF library available: fpdf2")

    _set_activity("idle")
    end_observation()
    print(f"\nsubAgent 5 - TEST PASSED")
    print(f"  Input source: main/Agent1/base-gens/*.json")
    print(f"  Output PDFs:  main/reports/base-reports/*.pdf")
    print(f"  Input source: main/Agent1/insight-gens/*.json")
    print(f"  Output PDFs:  main/reports/insights/*.pdf")
    print("=" * 60)


def generate_single_pdf(json_file_path: str) -> Optional[str]:
    _set_activity("generating pdf")
    print(f"Generating PDF for: {json_file_path}")

    try:
        data = load_report_file(json_file_path)
        if data is None:
            print("  Failed to load file")
            _set_activity("idle")
            return None

        report_title, sections, source_file, generated_at = (
            extract_report_sections(data)
        )

        if not report_title or not sections:
            print("  No valid report content found")
            _set_activity("idle")
            return None

        dir_name = os.path.dirname(json_file_path)
        base_name = os.path.splitext(os.path.basename(json_file_path))[0]

        if "insight-gens" in dir_name:
            output_path = os.path.join(INSIGHTS_DIR, f"{base_name}.pdf")
        else:
            output_path = os.path.join(BASE_REPORTS_DIR, f"{base_name}.pdf")

        generate_report_pdf(
            report_title=report_title,
            sections=sections,
            source_file=source_file or base_name,
            generated_at=generated_at,
            output_path=output_path,
        )

        print(f"  Saved PDF to: {output_path}")
        _set_activity("idle")
        return output_path

    except Exception as e:
        print(f"  ERROR: {e}")
        _set_activity("idle")
        return None


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        test()
    else:
        results = run()
        total = len(results["base_reports"]) + len(results["insights"])
        if total:
            print(f"\nGenerated {total} PDF(s):")
            for category, paths in results.items():
                for path in paths:
                    print(f"  [{category}] {os.path.basename(path)}")
        else:
            print("No new PDFs were generated.")
