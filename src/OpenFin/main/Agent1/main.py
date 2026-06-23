"""
Agent 1 Orchestrator
Key objective: Watch for uploaded data files and orchestrate the full analysis pipeline.
No LLM calls — only initiates sub-agents sequentially per specs.

Pipeline (per specs.md):
  1. Detect new data in main/data/uploaded-data/
  2. Run subAgent 1 → process CSVs → save to filtered-data/
  3. Start subAgent 5 observation
  4. Run subAgents 2, 3, 4 in parallel
  5. Run subAgent 5 to convert JSONs → PDFs
  6. Wait until all idle, end observation
"""
import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

# Import subagent entry points
from .subAgent1.main import run as sub1_run
from .subAgent2.main import run as sub2_run
from .subAgent3.main import run as sub3_run
from .subAgent4.main import run as sub4_run
from .subAgent5.main import run as sub5_run, start_observation as sub5_start, end_observation as sub5_end

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "uploaded-data")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")
# Uploaded_files for deduplication across runs
UPLOAD_REGISTER = os.path.join(os.path.dirname(__file__), "uploaded_files.json")


def _ensure_dirs():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "data", "filtered-data"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "base-gens"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "insight-gens"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "reports", "base-reports"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "reports", "insights"), exist_ok=True)


def _set_activity(status: str):
    """Write current activity to log.txt (overwrite, per specs)."""
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {status}\n"
    try:
        with open(LOG_FILE, "w") as f:
            f.write(line)
    except OSError:
        print(line, end="")
    print(f"[Agent 1] activity: {status}")


def _read_subagent_log(subagent_dir: str) -> str:
    """Read the last line of a subagent's log.txt to check activity."""
    log_path = os.path.join(os.path.dirname(__file__), subagent_dir, "log.txt")
    try:
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                content = f.read().strip()
                return content
    except OSError:
        pass
    return ""


def _is_subagent_idle(subagent_dir: str) -> bool:
    """Check if a subagent's log shows idle (strict match after timestamp)."""
    content = _read_subagent_log(subagent_dir)
    if not content:
        return False
    # Strip timestamp prefix if present (e.g. "[2026-06-22T04:37:09] idle")
    if "] " in content:
        status = content.split("] ", 1)[-1].strip()
    else:
        status = content.strip()
    return status == "idle"


def _wait_for_subagent_idle(subagent_dir: str, label: str, timeout: int = 300):
    """Poll subagent log until idle appears or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        if _is_subagent_idle(subagent_dir):
            print(f"  [{label}] is idle")
            return True
        time.sleep(1)
    print(f"  [{label}] TIMEOUT after {timeout}s — proceeding anyway")
    return False


def _scan_new_files() -> List[str]:
    """Scan upload directory for new files not yet processed."""
    _ensure_dirs()
    processed = _load_register()
    files = []
    for fname in sorted(os.listdir(UPLOAD_DIR)):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath) and fname not in processed:
            files.append(fpath)
    return files


def _load_register() -> set:
    try:
        if os.path.exists(UPLOAD_REGISTER):
            with open(UPLOAD_REGISTER, "r") as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def _save_register(processed: set):
    try:
        with open(UPLOAD_REGISTER, "w") as f:
            json.dump(sorted(processed), f)
    except OSError:
        pass


def _mark_processed(filename: str):
    processed = _load_register()
    processed.add(filename)
    _save_register(processed)


def step_run_subagent1() -> bool:
    """Step 1: Run subAgent 1 to process all uploaded files."""
    _set_activity("running subAgent 1")
    print("\n" + "=" * 60)
    print("STEP 1: Running subAgent 1 (data processing)")
    print("=" * 60)

    try:
        results = sub1_run()
        if results:
            for fname, out in results.items():
                if out:
                    _mark_processed(fname)
                    print(f"  Processed: {fname} → {os.path.basename(out)}")
                else:
                    print(f"  Failed: {fname}")
            _wait_for_subagent_idle("subAgent1", "subAgent 1")
            return True
        else:
            print("  No files to process")
            return False
    except Exception as e:
        print(f"  ERROR in subAgent 1: {e}")
        traceback.print_exc()
        return False


def step_start_subagent5():
    """Step 2: Start subAgent 5 observation."""
    _set_activity("starting subAgent 5 observation")
    print("\n" + "=" * 60)
    print("STEP 2: Starting subAgent 5 observation")
    print("=" * 60)
    try:
        sub5_start()
        print("  Observation started — watching base-gens and insight-gens")
    except Exception as e:
        print(f"  ERROR: {e}")


def step_run_parallel_agents(use_llm: bool = True) -> Dict[str, Any]:
    """Step 3: Run subAgents 2, 3, and 4 in parallel."""
    _set_activity("running subAgents 2, 3, 4 in parallel")
    print("\n" + "=" * 60)
    print("STEP 3: Running subAgents 2, 3, 4 in parallel")
    print("=" * 60)

    results = {}

    def run_agent(label, func):
        try:
            r = func(use_llm=use_llm)
            return label, r
        except Exception as e:
            print(f"  [{label}] ERROR: {e}")
            traceback.print_exc()
            return label, None

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_agent, "subAgent 2", sub2_run): "subAgent 2",
            executor.submit(run_agent, "subAgent 3", sub3_run): "subAgent 3",
            executor.submit(run_agent, "subAgent 4", sub4_run): "subAgent 4",
        }
        for future in as_completed(futures):
            try:
                label, data = future.result()
                results[label] = data
                count = len(data) if isinstance(data, dict) else 0
                print(f"  [{label}] completed — {count} report(s) generated")
            except Exception as e:
                label = futures[future]
                print(f"  [{label}] FAILED: {e}")
                results[label] = None

    return results


def step_finalize_subagent5(wait_seconds: float = 5.0) -> int:
    """
    Step 4 (final): Wait briefly for subAgent 5's watcher to drain any
    straggler JSONs that arrived after subAgents 2/3/4 finished, then run
    one final one-shot batch pass to guarantee every JSON has a PDF.

    Returns the number of PDFs generated in this final pass.
    """
    _set_activity("finalizing subAgent 5 PDFs")
    print("\n" + "=" * 60)
    print("STEP 4: Finalizing subAgent 5 PDFs (watcher drain + final pass)")
    print("=" * 60)
    # Give the watcher a couple of poll cycles to handle anything still in flight.
    print(f"  Waiting {wait_seconds:.1f}s for watcher to drain…")
    time.sleep(wait_seconds)
    try:
        results = sub5_run()
        base_count = len(results.get("base_reports", []))
        insight_count = len(results.get("insights", []))
        total = base_count + insight_count
        print(f"  Final-pass PDFs: {base_count} base reports, "
              f"{insight_count} insights ({total} total)")
        return total
    except Exception as e:
        print(f"  ERROR in subAgent 5 final pass: {e}")
        traceback.print_exc()
        return 0


def step_end_subagent5():
    """Step 5: End subAgent 5 observation."""
    _set_activity("ending subAgent 5 observation")
    print("\n" + "=" * 60)
    print("STEP 5: Ending subAgent 5 observation")
    print("=" * 60)
    try:
        sub5_end()
        print("  Observation ended")
    except Exception as e:
        print(f"  ERROR: {e}")


def step_verify_results():
    """Step 6: Verify all outputs."""
    print("\n" + "=" * 60)
    print("STEP 6: Verifying outputs")
    print("=" * 60)

    base_gens = os.path.join(os.path.dirname(__file__), "base-gens")
    insight_gens = os.path.join(os.path.dirname(__file__), "insight-gens")
    base_reports = os.path.join(PROJECT_ROOT, "reports", "base-reports")
    insights_dir = os.path.join(PROJECT_ROOT, "reports", "insights")

    for label, path in [
        ("base-gens JSONs", base_gens),
        ("insight-gens JSONs", insight_gens),
        ("base-reports PDFs", base_reports),
        ("insights PDFs", insights_dir),
    ]:
        count = 0
        if os.path.isdir(path):
            count = len([f for f in os.listdir(path) if f.endswith((".json", ".pdf"))])
        print(f"  {label}: {count} files")

    # Print subagent statuses
    print("\n  Subagent statuses:")
    for sub in ["subAgent1", "subAgent2", "subAgent3", "subAgent4", "subAgent5"]:
        content = _read_subagent_log(sub)
        if content:
            print(f"    {sub}: {content[-80:]}")
        else:
            print(f"    {sub}: (no log)")


def run_pipeline(use_llm: bool = True) -> Dict[str, Any]:
    """
    Run the full Agent 1 pipeline once.
    Processes any files in uploaded-data through all subagents.

    Returns:
        Dict with pipeline results summary.
    """
    _set_activity("starting pipeline")
    print("\n" + "█" * 60)
    print("█  AGENT 1 — ORCHESTRATOR")
    print("█  Time: " + datetime.now().isoformat(timespec="seconds"))
    print("█" * 60)

    overall_start = time.time()
    pipeline_results = {
        "started": datetime.now().isoformat(timespec="seconds"),
        "subAgent1_ok": False,
        "subAgent2_reports": 0,
        "subAgent3_reports": 0,
        "subAgent4_reports": 0,
        "subAgent5_pdfs": 0,
    }

    # Step 1: Run subAgent 1
    pipeline_results["subAgent1_ok"] = step_run_subagent1()
    if not pipeline_results["subAgent1_ok"]:
        _set_activity("idle — no files processed")
        print("\n  No files processed. Pipeline ends.")
        pipeline_results["status"] = "no_files"
        return pipeline_results

    # Step 2: Start subAgent 5 observation (background daemon watcher)
    step_start_subagent5()

    # Step 3: Run subAgents 2, 3, 4 in parallel.
    # The subAgent 5 watcher runs concurrently in its own thread and will
    # generate PDFs for any JSON that lands in base-gens/ or insight-gens/
    # while these agents are still running.
    parallel_results = step_run_parallel_agents(use_llm=use_llm)

    for label, key in [("subAgent 2", "subAgent2_reports"),
                       ("subAgent 3", "subAgent3_reports"),
                       ("subAgent 4", "subAgent4_reports")]:
        r = parallel_results.get(label) or {}
        pipeline_results[key] = len(r) if isinstance(r, dict) else 0

    # Wait for parallel agents to show idle
    for sub, label in [("subAgent2", "subAgent 2"), ("subAgent3", "subAgent 3"),
                       ("subAgent4", "subAgent 4")]:
        _wait_for_subagent_idle(sub, label)

    # Step 4: Final pass for subAgent 5 — drain any straggler JSONs then
    # do a synchronous final scan to guarantee all PDFs exist.
    pdf_count = step_finalize_subagent5(wait_seconds=5.0)
    pipeline_results["subAgent5_pdfs"] = pdf_count
    _wait_for_subagent_idle("subAgent5", "subAgent 5")

    # Step 5: End subAgent 5 observation
    step_end_subagent5()

    # Step 6: Verify results
    step_verify_results()

    overall_elapsed = time.time() - overall_start
    _set_activity("idle")
    pipeline_results["status"] = "ok"
    pipeline_results["elapsed_seconds"] = round(overall_elapsed, 1)

    print("\n" + "█" * 60)
    print(f"█  AGENT 1 — PIPELINE COMPLETE ({overall_elapsed:.1f}s)")
    print("█" * 60)

    return pipeline_results


def watch_and_run(poll_interval: float = 5.0, max_iterations: int = 10):
    """
    Continuously watch for new files and run pipeline on each batch.

    Args:
        poll_interval: Seconds between polls for new files.
        max_iterations: Maximum pipeline runs before exiting.
    """
    _set_activity("watching for uploads")
    iteration = 0

    print(f"\nWatching {UPLOAD_DIR}/ for new files...")
    print(f"Poll interval: {poll_interval}s, max iterations: {max_iterations}")

    while iteration < max_iterations:
        new_files = _scan_new_files()

        if new_files:
            iteration += 1
            print(f"\n{'#' * 60}")
            print(f"# ITERATION {iteration}: Found {len(new_files)} new file(s)")
            for f in new_files:
                print(f"#   - {os.path.basename(f)}")
            print(f"{'#' * 60}")

            run_pipeline()
        else:
            _set_activity("idle — waiting for uploads")
            if iteration == 0 and poll_interval > 2:
                # First poll with no files: show status
                already = _load_register()
                print(f"  No new files. ({len(already)} already processed)")
            time.sleep(poll_interval)

    _set_activity("idle — watch ended")
    print(f"\nWatch ended after {iteration} pipeline run(s)")


def run_once(use_llm: bool = True) -> Dict[str, Any]:
    """Run the pipeline once on any available files (no watch loop)."""
    new_files = _scan_new_files()
    if not new_files:
        print("No new files in upload directory.")
        return {"status": "no_files"}
    return run_pipeline(use_llm=use_llm)


if __name__ == "__main__":
    import sys

    use_llm = "--heuristic" not in sys.argv

    if "--watch" in sys.argv:
        try:
            watch_and_run()
        except KeyboardInterrupt:
            print("\n\nInterrupted. Cleaning up...")
            _set_activity("idle")
    elif "--status" in sys.argv:
        print("\nAGENT 1 STATUS:")
        print(f"  Activity: {_read_subagent_log('')}")
        for sub in ["subAgent1", "subAgent2", "subAgent3", "subAgent4", "subAgent5"]:
            content = _read_subagent_log(sub)
            status = "idle" if "idle" in content.lower() else content
            print(f"  {sub}: {status}")
    else:
        run_once(use_llm=use_llm)
