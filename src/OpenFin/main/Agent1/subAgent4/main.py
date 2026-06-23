"""
main.py
Key objective: Orchestrate the full subAgent4 pipeline:
  1. Load filtered metrics from main/data/filtered-data/
  2. Use LLM to identify potential financial issues and inefficiencies
  3. Filter out issues that already have existing insight reports
  4. Generate professional reports for each identified issue
  5. Save reports to main/Agent1/insight-gens/
  6. Return organized financial issue insight data

Also provides a status/active-log facility readable by Agent 1.

Pipeline (per specs.md):
    Main run function initiated
    - LLM identifies potential issues
    - Identified and reported issues filtered
    - Professional reports generated for each issue
"""
import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from .data_access import (
    load_all_metrics,
    get_existing_insight_files,
    issue_to_insight_filename,
    save_insight,
)
from .financial_analyzer import (
    identify_financial_issues,
    generate_issue_report,
    heuristic_identify_issues,
    heuristic_generate_issue_report,
)

# ── Activity Log ───────────────────────────────────
# Per specs: maintain log.txt with current activity only (no past activity).
# Activities: "assessing issues", "idle"

LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")


def _set_activity(status: str):
    """Write current activity to log.txt (overwrite, per specs)."""
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {status}\n"
    try:
        with open(LOG_FILE, "w") as f:
            f.write(line)
    except OSError:
        print(line, end="")
    # Also print for debugging
    print(f"  [activity] {status}")


# ──────────────────────────────────────────────────
# Pipeline Steps
# ──────────────────────────────────────────────────


def step_load_metrics() -> List[Dict[str, Any]]:
    """
    Step 1: Load all filtered metrics from main/data/filtered-data/.

    Returns:
        List of metric dicts (one per filtered dataset).
    """
    _set_activity("assessing issues")
    print("Loading filtered metrics from data/filtered-data/ ...")
    all_metrics = load_all_metrics()

    if not all_metrics:
        print("  No filtered data found. Waiting for subAgent1 results.")
    else:
        print(f"  Loaded {len(all_metrics)} filtered dataset(s)")

    return all_metrics


def _merge_issue_plans(
    primary_plan: Dict[str, Any],
    secondary_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge two issue plans, keeping issues from both without duplicates.
    Primary plan takes precedence for overlapping issue_ids.
    """
    merged_identified = list(primary_plan.get("identified_issues", []))
    merged_no_issue = list(primary_plan.get("no_issue_issues", []))

    existing_ids = {i.get("issue_id") for i in merged_identified}
    existing_no_ids = {i.get("issue_id") for i in merged_no_issue}

    for issue in secondary_plan.get("identified_issues", []):
        iid = issue.get("issue_id")
        if iid and iid not in existing_ids:
            merged_identified.append(issue)
            existing_ids.add(iid)

    for issue in secondary_plan.get("no_issue_issues", []):
        iid = issue.get("issue_id")
        if iid and iid not in existing_no_ids and iid not in existing_ids:
            merged_no_issue.append(issue)
            existing_no_ids.add(iid)

    return {"identified_issues": merged_identified, "no_issue_issues": merged_no_issue}


def step_identify_issues(
    merged_metrics: Dict[str, Any],
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    Step 2: Identify financial issues using LLM supplemented by heuristic analysis.

    Uses LLM first, then supplements with heuristic findings for issues
    the LLM may have missed. This ensures comprehensive issue coverage.

    Args:
        merged_metrics: All metrics merged into a single dict.
        use_llm: If True, use LLM supplemented by heuristics;
                 otherwise use heuristic only.

    Returns:
        Dict with keys: identified_issues (list of issue dicts),
                        no_issue_issues (list of skipped issue dicts).
    """
    _set_activity("assessing issues")
    print("  Identifying financial issues via LLM + heuristic supplement ...")

    llm_plan = {"identified_issues": [], "no_issue_issues": []}
    heuristic_plan = heuristic_identify_issues(merged_metrics)

    if use_llm:
        try:
            llm_plan = identify_financial_issues(merged_metrics)
        except Exception as e:
            print(f"  LLM issue identification failed ({e}), using heuristic only.")
            llm_plan = {"identified_issues": [], "no_issue_issues": []}

    # Merge: LLM findings first (they have richer context), then heuristic supplement
    issue_plan = _merge_issue_plans(llm_plan, heuristic_plan)

    identified = issue_plan.get("identified_issues", [])
    no_issue = issue_plan.get("no_issue_issues", [])

    print(f"  Identified issues: {len(identified)}")
    for issue in identified:
        print(f"    - {issue.get('issue_id')} (status: {issue.get('status')}, "
             f"severity: {issue.get('severity')})")

    print(f"  Issues not indicated: {len(no_issue)}")
    for issue in no_issue:
        print(f"    - {issue.get('issue_id')}: {issue.get('reason', '')[:80]}")

    return issue_plan


def step_filter_existing_reports(
    issue_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Step 3: Filter out issues that already have an existing insight report.

    This ensures no existing reports get overwritten and avoids re-generating
    reports for issues already documented (per specs.md requirement).
    """
    existing_files = get_existing_insight_files()
    if not existing_files:
        return issue_plan

    identified = issue_plan.get("identified_issues", [])
    if not identified:
        return issue_plan

    filtered_identified = []
    deduped_no_issue = issue_plan.get("no_issue_issues", [])
    dedup_count = 0

    for issue in identified:
        issue_id = issue.get("issue_id", "")
        expected_filename = issue_to_insight_filename(issue_id)
        if expected_filename in existing_files:
            deduped_no_issue.append({
                "issue_id": issue_id,
                "reason": f"Report already exists ({expected_filename}.json)",
            })
            dedup_count += 1
            print(f"  Skipping {issue_id} — existing report found ({expected_filename}.json)")
        else:
            filtered_identified.append(issue)

    issue_plan["identified_issues"] = filtered_identified
    issue_plan["no_issue_issues"] = deduped_no_issue

    if dedup_count:
        print(f"  Filtered out {dedup_count} issue(s) with existing reports")

    return issue_plan


def step_generate_issue_reports(
    issue_plan: Dict[str, Any],
    merged_metrics: Dict[str, Any],
    use_llm: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    Step 4: Generate professional reports for each identified financial issue.

    Args:
        issue_plan: Dict with identified_issues list from step 2/3.
        merged_metrics: All metrics merged into a single dict.
        use_llm: If True, use LLM; otherwise heuristic fallback.

    Returns:
        Dict mapping report title → report data dict.
    """
    identified = issue_plan.get("identified_issues", [])
    if not identified:
        print("  No issues to generate reports for.")
        return {}

    insights = {}
    for issue in identified:
        issue_id = issue.get("issue_id", "")
        severity = issue.get("severity", "medium")
        rationale = issue.get("rationale", "")
        context = issue.get("context_for_report", "")
        key_metrics = issue.get("key_metrics", [])

        if not issue_id:
            continue

        _set_activity("assessing issues")
        print(f"  Generating report: {issue_id} (severity: {severity}) ...")
        start_time = time.time()

        try:
            if use_llm:
                report = generate_issue_report(
                    merged_metrics, issue_id, severity,
                    rationale, context, key_metrics,
                )
            else:
                report = heuristic_generate_issue_report(
                    merged_metrics, issue_id, severity,
                    rationale, context, key_metrics,
                )

            if report is None:
                print(f"    No profitable opportunity found for {issue_id} — skipping report.")
                continue

            # Attach metadata
            report_title = list(report.keys())[0] if report else issue_id
            if report_title in report:
                report[report_title]["_issue_id"] = issue_id
                report[report_title]["_issue_severity"] = severity
                report[report_title]["_generated_at"] = datetime.now().isoformat(
                    timespec="seconds"
                )
                report[report_title]["_source_file"] = merged_metrics.get(
                    "_source_file", "merged"
                )

            # Save to disk
            save_path = save_insight(report_title, report)
            print(f"    Saved to {os.path.basename(save_path)}")

            insights[report_title] = report

        except Exception as e:
            print(f"    ERROR generating {issue_id}: {e}")
            # Try heuristic fallback
            try:
                print(f"    Attempting heuristic fallback for {issue_id} ...")
                report = heuristic_generate_issue_report(
                    merged_metrics, issue_id, severity,
                    rationale, context, key_metrics,
                )
                if report:
                    insights[issue_id] = report
            except Exception as e2:
                print(f"    Heuristic fallback also failed: {e2}")

        elapsed = time.time() - start_time
        print(f"    Completed {issue_id} in {elapsed:.1f}s")

    return insights


def step_collect_results(
    insights: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Step 5: Collect and return all generated financial issue insight reports
    in the expected format.

    Spec format: {"report title": {"subheading": "content"...}}
    """
    output = {}
    for report_title, report_data in insights.items():
        clean_sections = {}
        sections = report_data.get(report_title, report_data)
        for header, content in sections.items():
            if not header.startswith("_"):
                clean_sections[header] = content
        if clean_sections:
            output[report_title] = clean_sections
    return output


# ──────────────────────────────────────────────────
# Main Entry Points
# ──────────────────────────────────────────────────


def run(
    use_llm: bool = True,
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Main run function (matching specs.md).

    Full pipeline:
      1. Load filtered metrics from main/data/filtered-data/
      2. Identify financial issues via LLM
      3. Filter out issues with existing reports
      4. Generate professional issue reports
      5. Save to main/Agent1/insight-gens/
      6. Return organized report data

    Args:
        use_llm: If True, use LLM; otherwise fall back to heuristics.

    Returns:
        Dict mapping report_title → {subheading: content}
    """
    _set_activity("assessing issues")
    print("=" * 60)
    print("subAgent4 — START")
    overall_start = time.time()

    # Step 1: Load metrics
    all_metrics = step_load_metrics()
    if not all_metrics:
        _set_activity("idle")
        print("No filtered data available. Exiting.")
        print("subAgent4 — END (no data)")
        return {}

    # Merge metrics from all datasets
    merged_metrics = {}
    for m in all_metrics:
        merged_metrics.update(m)

    # Step 2: Identify financial issues
    issue_plan = step_identify_issues(merged_metrics, use_llm=use_llm)
    if not issue_plan.get("identified_issues"):
        _set_activity("idle")
        print("No financial issues identified. Exiting.")
        print("subAgent4 — END (no issues)")
        return {}

    # Step 3: Filter out issues with existing insight reports
    issue_plan = step_filter_existing_reports(issue_plan)
    if not issue_plan.get("identified_issues"):
        _set_activity("idle")
        print("All identified issues already have existing reports. No new reports needed.")
        print("subAgent4 — END (no new issues)")
        return {}

    # Step 4: Generate issue reports
    insights = step_generate_issue_reports(
        issue_plan, merged_metrics, use_llm=use_llm
    )

    # Step 5: Collect results
    results = step_collect_results(insights)

    overall_elapsed = time.time() - overall_start
    _set_activity("idle")
    print(
        f"subAgent4 — END: generated {len(results)} "
        f"financial issue reports in {overall_elapsed:.1f}s"
    )
    print("=" * 60)

    return results


def run_with_data(
    metrics: Dict[str, Any],
    use_llm: bool = False,
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Run the full pipeline with in-memory metrics (for testing).
    Bypasses file loading from data/filtered-data/.

    Args:
        metrics: Pre-built metrics dict (same format as subAgent1 output).
        use_llm: If True, use LLM; otherwise heuristic only (safe for no-API testing).

    Returns:
        Dict mapping report_title → {subheading: content}
    """
    _set_activity("assessing issues")
    print("=" * 60)
    print("subAgent4 — START (test mode)")
    overall_start = time.time()

    # Use provided metrics directly
    merged_metrics = dict(metrics)
    merged_metrics["_source_file"] = "test_data_inline"
    print(f"Using in-code test metrics ({len(merged_metrics)} keys)")

    # Step 2: Identify financial issues
    issue_plan = step_identify_issues(merged_metrics, use_llm=use_llm)
    if not issue_plan.get("identified_issues"):
        _set_activity("idle")
        print("No financial issues identified. Exiting.")
        print("subAgent4 — END (no issues)")
        return {}

    # Step 3: Filter out issues with existing insight reports
    issue_plan = step_filter_existing_reports(issue_plan)
    if not issue_plan.get("identified_issues"):
        _set_activity("idle")
        print("All identified issues already have existing reports. No new reports needed.")
        print("subAgent4 — END (no new issues)")
        return {}

    # Step 4: Generate issue reports (heuristic for testing safety)
    insights = step_generate_issue_reports(
        issue_plan, merged_metrics, use_llm=use_llm
    )

    # Step 5: Collect results
    results = step_collect_results(insights)

    overall_elapsed = time.time() - overall_start
    _set_activity("idle")
    print(
        f"subAgent4 — END: generated {len(results)} "
        f"financial issue reports in {overall_elapsed:.1f}s"
    )
    print("=" * 60)

    return results


def _get_test_metrics() -> Dict[str, Any]:
    """Return sample metrics for testing (no file I/O required)."""
    return {
        "total_revenue": 1060830.00,
        "total_units_sold": 13540,
        "gross_profit": 350073.90,
        "net_profit": 212166.00,
        "gross_margin": 0.33,
        "net_margin": 0.20,
        "operating_margin": 0.25,
        "total_expenses": 710756.10,
        "expense_to_revenue_ratio": 0.67,
        "revenue_growth": 0.12,
        "profit_growth": 0.08,
        "expense_growth": 0.10,
        "customer_count": 150,
        "supplier_count": 8,
        "customer_retention_rate": 0.65,
        "repeat_purchase_rate": 0.40,
        "return_rate": 0.03,
        "refund_rate": 0.02,
        "discount_rate": 0.12,
        "average_order_value": 78.50,
        "highest_revenue_product": "Wireless Headphones",
        "highest_revenue_product_value": 243824.10,
        "lowest_revenue_product": "USB Hub",
        "lowest_revenue_product_value": 45620.00,
        "highest_profit_product": "Wireless Headphones",
        "highest_profit_product_value": 80461.95,
        "lowest_profit_product": "USB Hub",
        "lowest_profit_product_value": 9124.00,
        "highest_margin_product": "Screen Protector",
        "highest_margin_product_value": 0.55,
        "lowest_margin_product": "USB Hub",
        "lowest_margin_product_value": 0.27,
        "highest_selling_product": "Charging Cable",
        "highest_selling_product_units": 4200,
        "lowest_selling_product": "Docking Station",
        "lowest_selling_product_units": 340,
        "marketing_spend": 52100.00,
        "marketing_roi": 0.35,
        "shipping_costs": 32500.00,
        "revenue_per_employee": 212166.00,
        "profit_per_employee": 42433.20,
        "inventory_value": 185000.00,
        "inventory_turnover": 2.5,
        "average_inventory_age": 146.0,
        "inventory_growth_rate": 0.18,
        "accounts_receivable": 189000.00,
        "average_collection_period": 65.0,
        "accounts_payable": 52000.00,
        "average_payment_period": 28.0,
        "operating_cashflow": -25000.00,
        "cash_reserves": 15000.00,
        "cash_burn_rate": -18500.00,
        "cash_runway": 0.8,
        "revenue_concentration_score": 0.35,
        "customer_concentration_score": 0.15,
        "supplier_concentration": 0.42,
        "return_on_investment": 0.03,
        "return_on_assets": 0.04,
        "return_on_equity": 0.05,
        "working_capital": -15000.00,
        "debt_to_equity_ratio": 2.5,
        "current_ratio": 0.9,
        "revenue_volatility": 0.35,
        "profit_volatility": 0.42,
        "forecasted_revenue": 1180000.00,
        "forecasted_profit": 236000.00,
        "_source_file": "test_data_inline",
        "_processed_at": datetime.now().isoformat(timespec="seconds"),
        "_analysis_summary": "Test data with intentionally stressed metrics for subAgent4 compliance verification.",
    }


# Allow running directly for testing
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("subAgent4 — TEST MODE (in-code data, no file I/O)")
    print("=" * 60)

    test_metrics = _get_test_metrics()
    results = run_with_data(test_metrics, use_llm=False)

    if results:
        print(f"\nGenerated {len(results)} financial issue report(s):")
        for title, sections in results.items():
            section_count = len(sections)
            issue_type = title.split(" — ")[0] if " — " in title else title
            print(f"\n  ┌─ {issue_type}")
            print(f"  │  Sections: {section_count}")
            for heading, content in sections.items():
                preview = content[:120].replace("\n", " ") if isinstance(content, str) else str(content)[:120]
                print(f"  │    [{heading}]: {preview}...")
            print(f"  └─")
    else:
        print("No financial issue reports were generated.")

    # Show activity log
    print(f"\nActivity log ({LOG_FILE}):")
    try:
        with open(LOG_FILE, "r") as f:
            print(f"  {f.read().strip()}")
    except OSError:
        print("  (log not available)")
