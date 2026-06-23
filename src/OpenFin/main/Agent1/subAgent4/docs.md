# subAgent4 — Directory Documentation

## Key Objective
Identifies financial leaks, inefficiencies, and gaps in a business's finances. SubAgent4 runs in parallel with subAgents 2 and 3: it loads filtered metrics from `main/data/filtered-data/`, uses an LLM (supplemented by heuristic analysis) to detect critical financial issues from a comprehensive list of 60+ known issues, and generates professional diagnostic reports with data-backed findings, root cause analysis, and actionable recommendations.

## Key Initiating Function / Call Process

The main run functions are `main.run()` (production) and `main.run_with_data()` (testing):

```
main.run()  [production — reads from files]
  ├─ step_load_metrics()
  │    └─ data_access.load_all_metrics()
  │         └─ Load JSON from main/data/filtered-data/
  │
  ├─ step_identify_issues()
  │    ├─ financial_analyzer.heuristic_identify_issues() [fast, runs always]
  │    └─ financial_analyzer.identify_financial_issues() [LLM, slower]
  │         └─ Results merged via _merge_issue_plans() 
  │
  ├─ step_filter_existing_reports()
  │    └─ data_access.get_existing_insight_files()
  │         └─ Check if insight for each issue already exists → skip duplicates
  │
  ├─ step_generate_issue_reports()
  │    └─ for each identified issue:
  │         financial_analyzer.generate_issue_report()
  │         ├─ LLM prompt: metrics + issue details → 6-section diagnostic report
  │         └─ Skip if no profitable opportunity found
  │         data_access.save_insight()
  │         └─ Save to main/Agent1/insight-gens/*.json
  │
  └─ step_collect_results()
       └─ Return {"Report Title": {"Subheading": "content", ...}}

main.run_with_data(metrics, use_llm=False)  [testing — bypasses file I/O]
  ├─ Uses provided in-memory metrics dict directly
  ├─ step_identify_issues(use_llm=False)  [heuristic only, no API needed]
  ├─ step_filter_existing_reports()
  ├─ step_generate_issue_reports()
  └─ step_collect_results()
```

## Tools / Algorithms Used

- **OpenRouter API (gpt-oss-120b:free)**: Intelligent financial issue identification and detailed diagnostic report generation via free LLM models.
- **Heuristic threshold analysis**: Complementary issue detection using hardcoded metric thresholds (e.g., revenue concentration > 15%, expense ratio > 80%, cash runway < 6 months, revenue per employee < $1000) — covers 30+ issue categories.
- **LLM + Heuristic merging**: Both LLM and heuristic analyses run in parallel and results are merged via `_merge_issue_plans()`. LLM findings take precedence, but heuristic identifies issues the LLM might miss (e.g., concentration risks, product mix issues, employee productivity concerns).
- **Metrics summarization**: Builds a comprehensive structured summary of ALL available metrics with data coverage notes, organized by category for optimal LLM context.
- **Bold issue identification prompt**: The LLM prompt explicitly encourages identifying issues from available data — "BE BOLD, not conservative" — and removes the previous overly cautious instruction that caused the LLM to reject all issues as "data not provided".
- **Issue deduplication**: Filters out issues that already have insight reports in the `insights/` directory to avoid overwriting. Also deduplicates within the identified issues list (merges duplicates with max severity and combined metrics).
- **No-opportunity detection**: LLM returns explicit `profitable_opportunity` boolean; reports with `false` are skipped (returns None).
- **JSON parsing with regex fallback**: Handles malformed LLM responses gracefully.
- **Narrowed exception handling**: API errors and JSON parsing errors are handled separately, preventing silent masking of unexpected bugs.
- **In-code testing**: `_get_test_metrics()` returns 60+ intentionally stressed metrics for testing without file I/O. `run_with_data()` accepts in-memory metrics and runs the full pipeline with heuristic-only fallback.

## Major Files

| File | Purpose |
|------|---------|
| `data_access.py` | Loads filtered-data JSON from subAgent1; saves insight JSONs to Agent1/insight-gens/; checks for existing insight files |
| `financial_analyzer.py` | OpenRouter LLM + heuristic for issue identification and 6-section diagnostic report generation |
| `main.py` | Orchestrates the full pipeline: load → identify (LLM+heuristic merge) → filter → generate → save → return |

## Major Functions / Classes

| File | Object | Parameters | Use |
|------|--------|------------|-----|
| data_access | `load_all_metrics()` | None | Load all filtered metrics from filtered-data/ |
| data_access | `get_existing_insight_files()` | None | Return set of existing insight filenames (dedup) |
| data_access | `issue_to_insight_filename(issue_id)` | `issue_id: str` | Map issue ID to expected insight filename |
| data_access | `save_insight(name, data)` | `name: str, data: dict` | Save financial issue insight JSON to Agent1/insight-gens/ |
| financial_analyzer | `ALL_FINANCIAL_ISSUES` | None (module-level list) | Master list of 67 known financial issues from specs.md |
| financial_analyzer | `identify_financial_issues(metrics)` | `metrics: dict` | LLM identifies which financial issues exist; falls back to heuristic if LLM returns empty |
| financial_analyzer | `generate_issue_report(metrics, issue_id, severity, rationale, context, key_metrics)` | `metrics: dict, issue_id: str, severity: str, rationale: str, context: str, key_metrics: list` | Generate 6-section diagnostic report via LLM; falls back to heuristic on API/parse failure |
| financial_analyzer | `build_identify_issues_prompt(metrics)` | `metrics: dict` | Build "BE BOLD" issue identification LLM prompt showing all available metrics |
| financial_analyzer | `build_issue_report_prompt(metrics, issue_id, severity, rationale, context, key_metrics)` | Same as generate | Build 6-section issue report LLM prompt with metrics context |
| financial_analyzer | `_summarize_metrics_for_issues(metrics)` | `metrics: dict` | Builds comprehensive categorized metric summary targeting financial issue detection |
| financial_analyzer | `heuristic_identify_issues(metrics)` | `metrics: dict` | Threshold-based issue detection covering 30+ categories (concentration, product mix, employee productivity, etc.) |
| financial_analyzer | `heuristic_generate_issue_report(metrics, issue_id, severity, rationale, context, key_metrics)` | Same as generate | Template fallback for issue report generation with available metric display |
| financial_analyzer | `_get_llm_client()` | None | Configure and return OpenAI client for OpenRouter |
| financial_analyzer | `_strip_json_fences(content)` | `content: str` | Remove markdown code fences from LLM response |
| financial_analyzer | `_parse_json_response(content)` | `content: str` | Parse LLM response as JSON with regex fallback |
| main | `run(use_llm)` | `use_llm: bool` | Main production entry: full pipeline (load → identify → filter → generate → return) |
| main | `run_with_data(metrics, use_llm)` | `metrics: dict, use_llm: bool` | Test entry: full pipeline with in-memory data, heuristic-only safe |
| main | `_get_test_metrics()` | None | Return 60+ stressed test metrics for issue detection verification |
| main | `_set_activity(status)` | `status: str` | Write current activity to log.txt (overwrite mode, specs-compliant) |
| main | `_merge_issue_plans(primary, secondary)` | `primary: dict, secondary: dict` | Merge two issue plans without duplicates; primary takes precedence |
| main | `step_identify_issues(metrics, use_llm)` | `metrics: dict, use_llm: bool` | Run LLM + heuristic and merge results for comprehensive coverage |
| main | `step_filter_existing_reports(issue_plan)` | `issue_plan: dict` | Filter out issues with existing insight reports |
| main | `step_generate_issue_reports(issue_plan, metrics, use_llm)` | `issue_plan: dict, metrics: dict, use_llm: bool` | Generate diagnostic reports for each identified issue |
| main | `step_collect_results(insights)` | `insights: dict` | Strip metadata and return in spec format |

## Financial Issues Detected (60+ from specs.md)

**Revenue & Growth:** declining_revenue, slowing_revenue_growth, volatile_revenue_streams, declining_business_growth, reduced_market_demand

**Profit & Margins:** declining_profit, slowing_profit_growth, margin_compression, declining_gross_margin, declining_net_margin, declining_operating_margin, volatile_profitability, unsustainable_growth_patterns

**Expenses:** excessive_expense_growth, expenses_growing_faster_than_revenue, high_operating_costs, excessive_payroll_costs, payroll_growing_faster_than_revenue, excessive_fixed_costs, inefficient_resource_allocation

**Cash Flow:** declining_cash_flow, low_cash_reserves, high_cash_burn_rate, cash_flow_bottlenecks, poor_working_capital_management

**Accounts Receivable/Payable:** increasing_accounts_receivable, overdue_customer_payments, poor_collection_efficiency, increasing_accounts_payable

**Inventory:** declining_inventory_turnover, excess_inventory_levels, overstocked_products, understocked_products, slow_moving_inventory, dead_inventory, excessive_inventory_carrying_costs, inventory_growth_exceeding_sales_growth, poor_inventory_management, seasonal_inventory_mismatch

**Products:** declining_product_sales, declining_product_profitability, underperforming_products, inefficient_product_mix, low_margin_high_volume_products, high_margin_low_volume_products, declining_product_lifecycle

**Customers:** declining_customer_retention, declining_repeat_purchase_rate, declining_average_order_value, high_refund_rates, excessive_discounting, customer_dependency_risk, customer_concentration_risk

**Suppliers:** rising_supplier_costs, supplier_dependency_risk, supplier_concentration_risk

**Employees:** declining_revenue_per_employee, declining_profit_per_employee

**Ratios & Health:** poor_return_on_investment, poor_return_on_assets, poor_return_on_equity, declining_operational_efficiency, increasing_financial_risk, declining_financial_health, revenue_concentration_risk, profit_concentration_risk, underperforming_sales_periods

## Data Flow

```
subAgent1 output: main/data/filtered-data/*.json
  │  (computed_metrics + llm_analysis + column_mappings)
  ▼
data_access.load_all_metrics()
  │  → List of metric dicts with metadata
  ▼
financial_analyzer.heuristic_identify_issues() [always runs]
  │  → Threshold-based detection: concentration, product mix, productivity, etc.
  ▼
financial_analyzer.identify_financial_issues() [LLM, runs in parallel]
  │  → LLM: "Analyze metrics and identify leaks/inefficiencies — BE BOLD"
  │  → { identified_issues: [...], no_issue_issues: [...] }
  ▼
_merge_issue_plans(LLM_result, heuristic_result)
  │  → Combined issue list (LLM takes precedence, heuristic fills gaps)
  ▼
data_access.get_existing_insight_files() [deduplication]
  │  → Skip issues with existing reports
  ▼
financial_analyzer.generate_issue_report() [for each issue]
  │  → 6-section diagnostic report:
  │    Executive Summary, Data & Evidence, Detailed Analysis,
  │    Root Causes, Recommendations, Expected Impact
  │  → Skip if no profitable opportunity found
  │  → Fallback to heuristic_generate_issue_report() on failure
  ▼
data_access.save_insight()
  │  → Saved to main/Agent1/insight-gens/*_financial_issue_research.json
  ▼
Returned to Agent 1 as:
  { "Issue Title Financial Issue Research": { "Section": "content", ... } }
```

## Report Format (per specs.md)

Each generated issue report follows this structure:
```json
{
  "Revenue Concentration Risk Financial Issue Research": {
    "Executive Summary": "This report analyzes revenue concentration risk...",
    "Data & Evidence": "Revenue is $1,060,829.50 with Wireless Headphones at $243,824.10...",
    "Detailed Analysis": "Several factors contribute to this concentration...",
    "Root Causes": "The primary root causes identified are...",
    "Recommendations": "1. Diversify the product portfolio...\\n2. Rebalance marketing spend...",
    "Expected Impact": "Resolving this issue could recover approximately $X..."
  }
}
```

## Deduplication Strategy

### Within-run dedup (heuristic_identify_issues)
When the heuristic analysis generates duplicate issue_ids (e.g., "inefficient_product_mix" detected from both ratio analysis and margin analysis), the dedup logic at the end of `heuristic_identify_issues()` merges them:
- Keeps the first occurrence
- Concatenates rationale strings
- Uses max severity across duplicates
- Combines key_metrics lists

### Cross-run dedup (step_filter_existing_reports)
Before generating a new issue report, subAgent4 checks `main/Agent1/insight-gens/` for existing files matching the pattern `{issue_id}_financial_issue_research.json`. If a report already exists for an issue, that issue is skipped. This prevents overwriting existing reports and avoids regenerating insights for already-documented issues.

### LLM + Heuristic dedup (_merge_issue_plans)
When merging LLM and heuristic results, the LLM findings take precedence. If both identify the same issue_id, the LLM's version is kept and the heuristic's version is discarded. This ensures the LLM's richer context is preserved while still catching issues the LLM missed.
