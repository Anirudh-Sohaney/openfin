"""
main.py
Key objective: Orchestrate the full subAgent3 pipeline:
  1. Load filtered metrics from main/data/filtered-data/
  2. Use LLM to identify which research topics to pursue
  3. Search the internet via Tavily API for each topic
  4. Generate research insight reports combining metrics + search results
  5. Save insights to main/Agent1/insight-gens/
  6. Return organized research reports

Also provides a status/active-log facility readable by Agent 1.
"""
import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from .data_access import (
    load_all_metrics,
    save_insight,
    get_existing_insight_files,
    topic_to_insight_filename,
)
from .tavily_search import build_search_queries, search_topics
from .research_analyzer import (
    identify_research_topics,
    generate_research_report,
    heuristic_identify_topics,
)

# ── Activity Log ───────────────────────────────────
# Per specs: maintain log.txt with current activity only (no past activity).
# Activities: "researching online", "comparing suppliers",
#             "researching products", "analyzing", "generating report", "idle"

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
    """
    _set_activity("researching online")
    print("Loading filtered metrics from data/filtered-data/ ...")
    all_metrics = load_all_metrics()

    if not all_metrics:
        print("  No filtered data found. Waiting for subAgent1 results.")
    else:
        print(f"  Loaded {len(all_metrics)} filtered dataset(s)")

    return all_metrics


def step_identify_topics(
    merged_metrics: Dict[str, Any],
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    Step 2: Use LLM to identify which research topics to pursue.
    Falls back to heuristic selection if LLM is unavailable.

    Returns the topic plan dict with prioritized_topics, product_categories, industry.
    """
    _set_activity("analyzing")
    if not use_llm:
        print("  Identifying research topics via heuristic (use_llm=False) ...")
        return heuristic_identify_topics(merged_metrics)

    print("  Identifying research topics via LLM ...")
    try:
        topic_plan = identify_research_topics(merged_metrics)
        if not topic_plan.get("prioritized_topics"):
            print("  LLM returned no topics — using heuristic fallback.")
            topic_plan = heuristic_identify_topics(merged_metrics)
    except Exception as e:
        print(f"  LLM topic identification failed ({e}), using heuristic fallback.")
        topic_plan = heuristic_identify_topics(merged_metrics)

    prioritized = topic_plan.get("prioritized_topics", [])
    skipped = topic_plan.get("skipped_topics", [])

    print(f"  Prioritized topics: {len(prioritized)}")
    for t in prioritized:
        print(f"    - {t.get('topic')} (priority: {t.get('priority', 'unknown')})")

    print(f"  Skipped topics: {len(skipped)}")
    for t in skipped:
        print(f"    - {t.get('topic')}: {t.get('reason', 'unknown')}")

    return topic_plan


def step_filter_existing_reports(
    topic_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Step 2b: Filter out topics that already have an existing insight report.

    This ensures no existing reports get overwritten and re-generating
    topics with existing research is avoided (per specs.md requirement).
    """
    existing_files = get_existing_insight_files()
    if not existing_files:
        return topic_plan

    prioritized = topic_plan.get("prioritized_topics", [])
    if not prioritized:
        return topic_plan

    filtered_prioritized = []
    deduped_skipped = topic_plan.get("skipped_topics", [])
    dedup_count = 0

    for t in prioritized:
        topic = t.get("topic", "")
        expected_filename = topic_to_insight_filename(topic)
        if expected_filename in existing_files:
            deduped_skipped.append({
                "topic": topic,
                "reason": f"Report already exists ({expected_filename}.json)",
            })
            dedup_count += 1
            print(f"  Skipping {topic} — existing report found ({expected_filename}.json)")
        else:
            filtered_prioritized.append(t)

    topic_plan["prioritized_topics"] = filtered_prioritized
    topic_plan["skipped_topics"] = deduped_skipped

    if dedup_count:
        print(f"  Filtered out {dedup_count} topic(s) with existing reports")

    return topic_plan


def step_search_internet(
    topic_plan: Dict[str, Any],
    max_results_per_topic: int = 4,
    use_llm: bool = True,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Step 3: Search the internet via Tavily API for each prioritized topic.
    """
    prioritized = topic_plan.get("prioritized_topics", [])
    if not use_llm:
        print("  Skipping Tavily search (use_llm=False). Generating metric-only reports.")
        return {t.get("topic"): None for t in prioritized}
    if not prioritized:
        print("  No topics to search.")
        return {}

    product_categories = topic_plan.get("product_categories", "consumer electronics")
    industry = topic_plan.get("industry", "consumer electronics retail")

    # Extract topic info — build per-topic queries using context_for_search
    topic_specs = []
    for t in prioritized:
        topic = t.get("topic", "")
        if topic:
            topic_specs.append({
                "topic": topic,
                "context": t.get("context_for_search", ""),
            })

    _set_activity("researching online")
    print(f"  Searching {len(topic_specs)} topics via Tavily ...")
    queries = build_search_queries(
        [s["topic"] for s in topic_specs],
        product_categories=product_categories,
        industry=industry,
        current_year=str(datetime.now().year),
        topic_contexts={s["topic"]: s["context"] for s in topic_specs if s["context"]},
    )

    try:
        search_results = search_topics(queries, max_results_per_topic=max_results_per_topic)
    except Exception as e:
        print(f"  Tavily search failed ({e}). Generating metric-only reports.")
        search_results = {t: None for t in queries}

    successful = sum(1 for v in search_results.values() if v is not None)
    print(f"  Search complete: {successful}/{len(search_results)} queries succeeded")

    return search_results


def step_generate_insights(
    topic_plan: Dict[str, Any],
    merged_metrics: Dict[str, Any],
    search_results: Dict[str, Optional[Dict[str, Any]]],
    use_llm: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    Step 4: Generate research insight reports combining metrics + search results.
    """
    prioritized = topic_plan.get("prioritized_topics", [])
    if not prioritized:
        print("  No topics to generate reports for.")
        return {}

    product_categories = topic_plan.get("product_categories", "consumer electronics")
    industry = topic_plan.get("industry", "consumer electronics retail")

    insights = {}
    for topic_info in prioritized:
        topic = topic_info.get("topic", "")
        priority = topic_info.get("priority", "medium")

        if not topic:
            continue

        _set_activity("generating report")
        print(f"  Generating insight report: {topic} (priority: {priority}) ...")
        start_time = time.time()

        topic_results = search_results.get(topic)

        try:
            if use_llm:
                report = generate_research_report(
                    merged_metrics,
                    topic,
                    topic_results,
                    product_categories=product_categories,
                    industry=industry,
                )
            else:
                from .research_analyzer import heuristic_generate_research_report
                report = heuristic_generate_research_report(
                    merged_metrics, topic,
                    product_categories=product_categories,
                    industry=industry,
                )

            if report is None:
                print(f"    No profitable solution found for {topic} — skipping report.")
                continue

            # Attach metadata
            report_title = list(report.keys())[0] if report else topic
            if report_title in report:
                report[report_title]["_topic"] = topic
                report[report_title]["_priority"] = priority
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
            print(f"    ERROR generating {topic}: {e}")

        elapsed = time.time() - start_time
        print(f"    Completed {topic} in {elapsed:.1f}s")

    return insights


def step_collect_results(
    insights: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Step 5: Collect and return all research insight reports in the expected format.

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
    max_results_per_topic: int = 4,
    use_llm: bool = True,
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Main run function (matching specs.md).

    Full pipeline:
      1. Load filtered metrics from main/data/filtered-data/
      2. Identify research topics via LLM
      3. Search internet via Tavily API
      4. Generate research insight reports
      5. Save to main/Agent1/insight-gens/
      6. Return organized report data

    Args:
        max_results_per_topic: Max Tavily results per topic (default 4).
        use_llm: If True, use LLM + Tavily; if False, heuristic-only (no API needed).

    Returns:
        Dict mapping report_title → {subheading: content}
    """
    _set_activity("researching online")
    print("=" * 60)
    print("subAgent3 — START")
    overall_start = time.time()

    # Step 1: Load metrics
    all_metrics = step_load_metrics()
    if not all_metrics:
        _set_activity("idle")
        print("No filtered data available. Exiting.")
        print("subAgent3 — END (no data)")
        return {}

    # Merge metrics from all datasets
    merged_metrics = {}
    for m in all_metrics:
        merged_metrics.update(m)

    # Step 2: Identify research topics
    topic_plan = step_identify_topics(merged_metrics, use_llm=use_llm)
    if not topic_plan.get("prioritized_topics"):
        _set_activity("idle")
        print("No research topics identified. Exiting.")
        print("subAgent3 — END (no topics)")
        return {}

    # Step 2b: Filter out topics with existing insight reports
    topic_plan = step_filter_existing_reports(topic_plan)
    if not topic_plan.get("prioritized_topics"):
        _set_activity("idle")
        print("All topics already have existing reports. No new research needed.")
        print("subAgent3 — END (no new topics)")
        return {}

    # Step 3: Search internet (only for topics without existing reports)
    search_results = step_search_internet(
        topic_plan, max_results_per_topic=max_results_per_topic,
        use_llm=use_llm,
    )

    # Step 4: Generate insights
    insights = step_generate_insights(
        topic_plan, merged_metrics, search_results,
        use_llm=use_llm,
    )

    # Step 5: Collect results
    results = step_collect_results(insights)

    overall_elapsed = time.time() - overall_start
    _set_activity("idle")
    print(
        f"subAgent3 — END: generated {len(results)} "
        f"insight reports in {overall_elapsed:.1f}s"
    )
    print("=" * 60)

    return results


def run_with_data(
    metrics: Dict[str, Any],
    max_results_per_topic: int = 4,
    skip_search: bool = True,
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Run the full pipeline with in-memory metrics (for testing).
    Bypasses file loading from data/filtered-data/.

    Args:
        metrics: Pre-built metrics dict (same format as subAgent1 output).
        max_results_per_topic: Max Tavily results per topic (default 4).
        skip_search: If True, skip Tavily API and use metric-only reports.

    Returns:
        Dict mapping report_title → {subheading: content}
    """
    _set_activity("researching online")
    print("=" * 60)
    print("subAgent3 — START (test mode)")
    overall_start = time.time()

    # Use provided metrics directly
    merged_metrics = dict(metrics)
    merged_metrics["_source_file"] = "test_data_inline"
    print(f"Using in-code test metrics ({len(merged_metrics)} keys)")

    # Step 2: Identify research topics
    topic_plan = step_identify_topics(merged_metrics)
    if not topic_plan.get("prioritized_topics"):
        _set_activity("idle")
        print("No research topics identified. Exiting.")
        print("subAgent3 — END (no topics)")
        return {}

    # Step 2b: Filter out topics with existing insight reports
    topic_plan = step_filter_existing_reports(topic_plan)
    if not topic_plan.get("prioritized_topics"):
        _set_activity("idle")
        print("All topics already have existing reports. No new research needed.")
        print("subAgent3 — END (no new topics)")
        return {}

    # Step 3: Search internet or skip
    if skip_search:
        print("  Skipping Tavily search (test mode). Generating metric-only reports.")
        search_results = {t.get("topic"): None for t in topic_plan.get("prioritized_topics", [])}
    else:
        search_results = step_search_internet(
            topic_plan, max_results_per_topic=max_results_per_topic
        )

    # Step 4: Generate insights
    insights = step_generate_insights(
        topic_plan, merged_metrics, search_results
    )

    # Step 5: Collect results
    results = step_collect_results(insights)

    overall_elapsed = time.time() - overall_start
    _set_activity("idle")
    print(
        f"subAgent3 — END: generated {len(results)} "
        f"insight reports in {overall_elapsed:.1f}s"
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
        "marketing_roi": 3.5,
        "shipping_costs": 32500.00,
        "revenue_per_employee": 212166.00,
        "profit_per_employee": 42433.20,
        "inventory_value": 185000.00,
        "inventory_turnover": 5.73,
        "average_inventory_age": 63.7,
        "accounts_receivable": 89000.00,
        "average_collection_period": 32.0,
        "accounts_payable": 52000.00,
        "average_payment_period": 28.0,
        "operating_cashflow": 178000.00,
        "cash_reserves": 95000.00,
        "cash_burn_rate": 15200.00,
        "cash_runway": 6.25,
        "revenue_concentration_score": 0.35,
        "customer_concentration_score": 0.15,
        "supplier_concentration": 0.42,
        "return_on_investment": 0.15,
        "return_on_assets": 0.12,
        "return_on_equity": 0.18,
        "working_capital": 132000.00,
        "debt_to_equity_ratio": 0.85,
        "current_ratio": 2.1,
        "revenue_volatility": 0.22,
        "profit_volatility": 0.28,
        "forecasted_revenue": 1180000.00,
        "forecasted_profit": 236000.00,
        "_source_file": "test_data_inline",
        "_processed_at": datetime.now().isoformat(timespec="seconds"),
        "_analysis_summary": "Test data for subAgent3 compliance verification.",
    }


# Allow running directly for testing
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("subAgent3 — TEST MODE (in-code data, no file I/O)")
    print("=" * 60)

    test_metrics = _get_test_metrics()
    results = run_with_data(test_metrics, skip_search=True)

    if results:
        print(f"\nGenerated {len(results)} research insight report(s):")
        for title, sections in results.items():
            print(f"\n  ┌─ {title}")
            print(f"  │  Sections: {len(sections)}")
            for heading, content in sections.items():
                preview = content[:120].replace("\n", " ") if isinstance(content, str) else str(content)[:120]
                print(f"  │    [{heading}]: {preview}...")
            print(f"  └─")
    else:
        print("No research insights were generated.")

    # Show activity log
    print(f"\nActivity log ({LOG_FILE}):")
    try:
        with open(LOG_FILE, "r") as f:
            print(f"  {f.read().strip()}")
    except OSError:
        print("  (log not available)")

