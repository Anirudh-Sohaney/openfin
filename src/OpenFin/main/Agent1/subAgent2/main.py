import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

from .data_access import (
    load_all_metrics,
    get_existing_reports,
    load_existing_report,
    save_report,
    compare_metrics_for_report,
)
from .llm_interface import (
    identify_possible_reports,
    generate_report,
    heuristic_identify_reports,
    heuristic_generate_report,
)

LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")


def _set_activity(status: str):
    with open(LOG_FILE, "w") as f:
        f.write(status.strip() + "\n")


def step_load_metrics() -> List[Dict[str, Any]]:
    print("Loading filtered metrics from data/filtered-data/ ...")
    all_metrics = load_all_metrics()

    if not all_metrics:
        print("  No filtered data found.")
    else:
        print(f"  Loaded {len(all_metrics)} filtered dataset(s)")

    return all_metrics


def step_identify_reports(
    all_metrics: List[Dict[str, Any]],
    use_llm: bool = True,
) -> List[Dict[str, Any]]:
    existing = get_existing_reports()
    existing_names = list(existing.keys())
    print(f"  Existing reports: {existing_names if existing_names else 'none'}")

    _set_activity("thinking")
    print("  Identifying possible reports ...")
    try:
        if use_llm:
            result = identify_possible_reports(all_metrics, existing_names)
        else:
            result = heuristic_identify_reports(all_metrics, existing_names)
    except Exception as e:
        print(f"  LLM identification failed ({e}), using heuristic fallback.")
        result = heuristic_identify_reports(all_metrics, existing_names)

    possible = result.get("possible_reports", [])
    unavailable = result.get("unavailable_reports", [])

    print(f"  Possible reports: {len(possible)}")
    for r in possible:
        print(f"    - {r.get('report_name')} (confidence: {r.get('confidence', 'unknown')})")

    if unavailable:
        print(f"  Unavailable reports: {len(unavailable)}")
        for r in unavailable:
            print(f"    - {r.get('report_name')}: {r.get('reason', 'unknown reason')}")

    return possible


def step_filter_existing_reports(
    possible_reports: List[Dict[str, Any]],
    all_metrics: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not all_metrics:
        return possible_reports

    merged_metrics = {}
    for m in all_metrics:
        merged_metrics.update(m)

    filtered = []
    for report in possible_reports:
        report_name = report.get("report_name", "")
        old_report = load_existing_report(report_name)

        if old_report is not None:
            changed = compare_metrics_for_report(
                report_name, merged_metrics, old_report
            )
            if not changed:
                print(f"  Skipping '{report_name}' — already generated, metrics unchanged")
                continue
            else:
                print(f"  Regenerating '{report_name}' — metrics have changed")

        filtered.append(report)

    print(f"  Reports to generate after filtering: {len(filtered)}")
    return filtered


def step_generate_reports(
    reports_to_generate: List[Dict[str, Any]],
    all_metrics: List[Dict[str, Any]],
    use_llm: bool = True,
) -> Dict[str, Dict[str, Any]]:
    if not all_metrics or not reports_to_generate:
        return {}

    merged_metrics = {}
    analysis_summaries = []
    for m in all_metrics:
        merged_metrics.update(m)
        if m.get("_analysis_summary"):
            analysis_summaries.append(m["_analysis_summary"])

    combined_summary = " | ".join(analysis_summaries) if analysis_summaries else ""

    generated = {}
    for report in reports_to_generate:
        report_name = report.get("report_name", "Unknown Report")
        required = report.get("required_metrics", [])

        _set_activity(f"generating report for {report_name}")
        print(f"  Generating report: {report_name} ...")
        start_time = time.time()

        try:
            if use_llm:
                result = generate_report(
                    report_name, merged_metrics, required, combined_summary
                )
            else:
                result = heuristic_generate_report(
                    report_name, merged_metrics, required, combined_summary
                )

            if report_name in result:
                result[report_name]["_metrics_used"] = {
                    k: merged_metrics.get(k)
                    for k in required
                }
                result[report_name]["_source_file"] = merged_metrics.get(
                    "_source_file", "merged"
                )
                result[report_name]["_generated_at"] = datetime.now().isoformat(
                    timespec="seconds"
                )
                result[report_name]["_analysis_summary"] = combined_summary

            save_path = save_report(report_name, result)
            print(f"    Saved to {os.path.basename(save_path)}")

            generated[report_name] = result

        except Exception as e:
            print(f"    ERROR generating {report_name}: {e}")
            try:
                print(f"    Attempting heuristic fallback for {report_name} ...")
                result = heuristic_generate_report(
                    report_name, merged_metrics, required, combined_summary
                )
                generated[report_name] = result
            except Exception as e2:
                print(f"    Heuristic fallback also failed: {e2}")

        elapsed = time.time() - start_time
        print(f"    Completed {report_name} in {elapsed:.1f}s")

    _set_activity("idle")
    return generated


def step_collect_results(
    generated: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Dict[str, str]]]:
    output = {}
    for report_name, report_data in generated.items():
        clean_sections = {}
        sections = report_data.get(report_name, report_data)
        for header, content in sections.items():
            if not header.startswith("_"):
                clean_sections[header] = content
        if clean_sections:
            output[report_name] = clean_sections
    return output


def run(
    force_regenerate: bool = False,
    use_llm: bool = True,
) -> Dict[str, Dict[str, Dict[str, str]]]:
    _set_activity("thinking")
    print("=" * 60)
    print("subAgent 2 — START")
    overall_start = time.time()

    all_metrics = step_load_metrics()
    if not all_metrics:
        print("No filtered data available. Exiting.")
        _set_activity("idle")
        return {}

    possible_reports = step_identify_reports(all_metrics, use_llm=use_llm)
    if not possible_reports:
        print("No reports can be generated from available metrics. Exiting.")
        _set_activity("idle")
        return {}

    if force_regenerate:
        print("  Force regenerate enabled — generating all possible reports.")
        reports_to_generate = possible_reports
    else:
        reports_to_generate = step_filter_existing_reports(
            possible_reports, all_metrics
        )

    if not reports_to_generate:
        print("All possible reports are already up to date. Exiting.")
        _set_activity("idle")
        return {}

    generated = step_generate_reports(
        reports_to_generate, all_metrics, use_llm=use_llm
    )

    results = step_collect_results(generated)

    overall_elapsed = time.time() - overall_start
    print(f"subAgent 2 — END: generated {len(results)} reports in {overall_elapsed:.1f}s")
    print("=" * 60)
    _set_activity("idle")

    return results


def generate_single_report(
    report_name: str,
    use_llm: bool = True,
) -> Optional[Dict[str, Dict[str, str]]]:
    _set_activity(f"generating report for {report_name}")
    print(f"Generating single report: {report_name}")

    all_metrics = step_load_metrics()
    if not all_metrics:
        print("  No filtered data available.")
        _set_activity("idle")
        return None

    merged_metrics = {}
    for m in all_metrics:
        merged_metrics.update(m)

    from .llm_interface import heuristic_identify_reports
    h = heuristic_identify_reports([merged_metrics], [])
    required = []
    for r in h.get("possible_reports", []):
        if r.get("report_name", "").lower() == report_name.lower():
            required = r.get("required_metrics", [])
            break

    if not required:
        required = [k for k in merged_metrics.keys() if not k.startswith("_")]

    try:
        if use_llm:
            from .llm_interface import generate_report as gen
        else:
            gen = heuristic_generate_report

        summary = merged_metrics.get("_analysis_summary", "")
        result = gen(report_name, merged_metrics, required, summary)

        if report_name in result:
            result[report_name]["_metrics_used"] = {
                k: merged_metrics.get(k) for k in required
            }
            result[report_name]["_generated_at"] = datetime.now().isoformat(
                timespec="seconds"
            )

        save_report(report_name, result)
        _set_activity("idle")
        return step_collect_results({report_name: result})

    except Exception as e:
        print(f"  ERROR: {e}")
        _set_activity("idle")
        return None


def test():
    print("=" * 60)
    print("subAgent 2 — TEST MODE (inline mock data, no file I/O)")
    print("=" * 60)

    _set_activity("thinking")

    mock_metrics_data = {
        "revenue_column": "revenue",
        "sales_column": "sales",
        "total_revenue": 175000.0,
        "yearly_revenue": 175000.0,
        "monthly_revenue": 14583.33,
        "revenue_growth": 0.12,
        "total_sales": 162000.0,
        "yearly_sales": 162000.0,
        "sales_growth": 0.09,
        "average_order_value": 52.50,
        "total_units_sold": 3240,
        "highest_selling_product": "Widget A",
        "lowest_selling_product": "Gadget C",
        "highest_revenue_product": "Widget A",
        "lowest_revenue_product": "Gadget C",
        "gross_profit": 65000.0,
        "net_profit": 42000.0,
        "gross_margin": 0.37,
        "net_margin": 0.24,
        "operating_margin": 0.28,
        "profit_growth": 0.08,
        "total_expenses": 95000.0,
        "monthly_expenses": 7916.67,
        "expense_growth": 0.05,
        "expense_to_revenue_ratio": 0.54,
        "payroll_expenses": 45000.0,
        "payroll_to_revenue_ratio": 0.26,
        "marketing_spend": 12000.0,
        "marketing_roi": 14.58,
        "inventory_value": 38000.0,
        "inventory_turnover": 4.2,
        "inventory_turnover_days": 86.9,
        "accounts_receivable": 15000.0,
        "accounts_payable": 12000.0,
        "average_collection_period": 31.3,
        "average_payment_period": 25.1,
        "operating_cashflow": 40000.0,
        "free_cashflow": 32000.0,
        "cash_reserves": 85000.0,
        "customer_count": 150,
        "customer_growth_rate": 0.15,
        "customer_retention_rate": 0.78,
        "average_customer_value": 1166.67,
        "supplier_count": 12,
        "largest_supplier_spend": 28000.0,
        "debt_to_equity_ratio": 0.45,
        "current_ratio": 2.1,
        "working_capital": 55000.0,
        "return_on_assets": 0.12,
        "return_on_equity": 0.18,
        "customer_concentration_score": 0.08,
        "revenue_concentration_score": 0.15,
        "seasonal_demand_score": 1.8,
        "peak_sales_month": "2025-12",
        "lowest_sales_month": "2025-02",
        "_source_file": "test_data.csv",
        "_processed_at": "2025-12-01T00:00:00",
        "_analysis_summary": "Test dataset with 12 months of revenue, expense, and sales data.",
    }

    all_metrics = [mock_metrics_data]

    print("\nIdentifying possible reports from mock metrics...")
    possible = heuristic_identify_reports(all_metrics, [])
    possible_reports = possible.get("possible_reports", [])

    print(f"\nPossible reports ({len(possible_reports)}):")
    for r in possible_reports:
        print(f"  - {r['report_name']} ({len(r['required_metrics'])} metrics)")

    print("\nGenerating sample reports (heuristic fallback)...")
    merged = {}
    for m in all_metrics:
        merged.update(m)

    generated = {}
    for report in possible_reports[:3]:
        name = report["report_name"]
        _set_activity(f"generating report for {name}")
        required = report["required_metrics"]
        result = heuristic_generate_report(name, merged, required, "Test dataset")
        generated[name] = result
        print(f"  Generated: {name}")
        sections = result.get(name, {})
        for sec in sections:
            if not sec.startswith("_"):
                content = sections[sec]
                print(f"    {sec}: {content[:80]}...")

    results = step_collect_results(generated)
    print(f"\nCollected {len(results)} clean report(s)")
    for name, sections in results.items():
        print(f"  - {name} ({len(sections)} sections)")

    _set_activity("idle")
    print("\nsubAgent 2 — TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        test()
    else:
        use_llm = "--heuristic" not in sys.argv
        force = "--force" in sys.argv
        results = run(force_regenerate=force, use_llm=use_llm)

        if results:
            print(f"\nGenerated {len(results)} report(s):")
            for name, sections in results.items():
                section_count = len(sections)
                print(f"  - {name} ({section_count} sections)")
        else:
            print("No reports were generated.")
