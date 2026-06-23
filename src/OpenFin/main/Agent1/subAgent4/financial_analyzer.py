"""
financial_analyzer.py
Key objective: Use LLM (via OpenRouter) to:
  1. Analyze financial metrics and identify critical financial issues and inefficiencies
  2. Generate professional financial issue reports with data backing, explanation, and advice

Uses OpenRouter API (OpenAI-compatible). Configure via environment variables:
    OPENAI_API_KEY  - OpenRouter API key (required)
    OPENAI_BASE_URL - Base URL (default: https://openrouter.ai/api/v1)
    LLM_MODEL       - Model name (default: openai/gpt-oss-120b:free)

Supported free models on OpenRouter:
    openai/gpt-oss-120b:free  (default, recommended for reasoning)
    openrouter/owl-alpha      (alternative free model)
"""
import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from main.llm_client import get_llm_client, get_model


# ── All known financial issues (from specs.md) ──────

ALL_FINANCIAL_ISSUES = [
    "declining_revenue",
    "slowing_revenue_growth",
    "declining_profit",
    "slowing_profit_growth",
    "margin_compression",
    "excessive_expense_growth",
    "expenses_growing_faster_than_revenue",
    "declining_cash_flow",
    "low_cash_reserves",
    "high_cash_burn_rate",
    "increasing_accounts_receivable",
    "overdue_customer_payments",
    "poor_collection_efficiency",
    "increasing_accounts_payable",
    "supplier_dependency_risk",
    "customer_dependency_risk",
    "revenue_concentration_risk",
    "profit_concentration_risk",
    "declining_inventory_turnover",
    "excess_inventory_levels",
    "overstocked_products",
    "understocked_products",
    "slow_moving_inventory",
    "dead_inventory",
    "declining_product_sales",
    "declining_product_profitability",
    "underperforming_products",
    "excessive_inventory_carrying_costs",
    "rising_supplier_costs",
    "excessive_payroll_costs",
    "payroll_growing_faster_than_revenue",
    "declining_revenue_per_employee",
    "declining_profit_per_employee",
    "declining_customer_retention",
    "declining_repeat_purchase_rate",
    "seasonal_inventory_mismatch",
    "declining_average_order_value",
    "high_refund_rates",
    "excessive_discounting",
    "declining_gross_margin",
    "declining_net_margin",
    "declining_operating_margin",
    "inventory_growth_exceeding_sales_growth",
    "poor_working_capital_management",
    "supplier_concentration_risk",
    "customer_concentration_risk",
    "high_operating_costs",
    "declining_financial_health",
    "volatile_revenue_streams",
    "volatile_profitability",
    "inefficient_product_mix",
    "low_margin_high_volume_products",
    "high_margin_low_volume_products",
    "cash_flow_bottlenecks",
    "poor_inventory_management",
    "underperforming_sales_periods",
    "declining_business_growth",
    "reduced_market_demand",
    "declining_product_lifecycle",
    "inefficient_resource_allocation",
    "excessive_fixed_costs",
    "poor_return_on_investment",
    "poor_return_on_assets",
    "poor_return_on_equity",
    "declining_operational_efficiency",
    "unsustainable_growth_patterns",
    "increasing_financial_risk",
]




def _strip_json_fences(content: str) -> str:
    """Remove markdown code fences from LLM response."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[-1].strip() == "```":
            content = "\n".join(lines[1:-1])
        else:
            content = "\n".join(lines[1:])
    return content.strip()


def _parse_json_response(content: str) -> Dict:
    """Parse LLM response as JSON, with fallback extraction."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"LLM returned invalid JSON: {content[:500]}")


# ──────────────────────────────────────────────────
# Step 1: Identify Financial Issues
# ──────────────────────────────────────────────────


def _summarize_metrics_for_issues(metrics: Dict[str, Any]) -> str:
    """
    Build a comprehensive summary of ALL available metrics.
    Shows every metric value that is present, organized by category,
    and also lists which metrics are MISSING so the LLM knows the data boundaries.
    """
    if not metrics:
        return "No metrics available."

    lines = []
    lines.append("=" * 60)
    lines.append("AVAILABLE METRICS — FULL DATA EXPORT")
    lines.append("=" * 60)

    # ── ALL available metrics, sorted ──
    available = {k: v for k, v in metrics.items() if v is not None and not k.startswith("_")}
    if available:
        lines.append("")
        lines.append("--- ALL AVAILABLE METRICS (raw dump) ---")
        for key in sorted(available.keys()):
            val = available[key]
            if isinstance(val, float):
                lines.append(f"  {key}: {val}")
            elif isinstance(val, dict):
                lines.append(f"  {key}: (dict with {len(val)} entries)")
            else:
                lines.append(f"  {key}: {val}")

    # ── Dedicated sections for clarity ──
    lines.append("")
    lines.append("--- DETAILED BREAKDOWN ---")

    def _fmt_val(v):
        if isinstance(v, float):
            return f"{v:,.2f}"
        return str(v)

    # Revenue & Growth
    rev = metrics.get("total_revenue")
    rev_growth = metrics.get("revenue_growth")
    if rev is not None:
        lines.append(f"\n  [REVENUE] Total Revenue: ${rev:,.2f}")
    if rev_growth is not None:
        lines.append(f"  [REVENUE] Revenue Growth Rate: {rev_growth * 100:.2f}%")
    monthly_rev = metrics.get("monthly_revenue")
    if monthly_rev is not None:
        lines.append(f"  [REVENUE] Avg Monthly Revenue: ${monthly_rev:,.2f}")
    quarterly_rev = metrics.get("quarterly_revenue")
    if quarterly_rev is not None:
        lines.append(f"  [REVENUE] Avg Quarterly Revenue: ${quarterly_rev:,.2f}")
    yearly_rev = metrics.get("yearly_revenue")
    if yearly_rev is not None:
        lines.append(f"  [REVENUE] Avg Yearly Revenue: ${yearly_rev:,.2f}")

    # Sales & Units
    total_units = metrics.get("total_units_sold")
    if total_units is not None:
        lines.append(f"  [SALES] Total Units Sold: {total_units}")
    aov = metrics.get("average_order_value")
    if aov is not None:
        lines.append(f"  [SALES] Avg Order Value: ${aov:,.2f}")

    # Profit & Margins
    for label, key in [
        ("Gross Profit", "gross_profit"),
        ("Net Profit", "net_profit"),
        ("Operating Profit", "operating_profit"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [PROFIT] {label}: ${val:,.2f}")

    for label, key in [
        ("Gross Margin", "gross_margin"),
        ("Net Margin", "net_margin"),
        ("Operating Margin", "operating_margin"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [MARGIN] {label}: {val * 100:.1f}%")

    profit_growth = metrics.get("profit_growth")
    if profit_growth is not None:
        lines.append(f"  [PROFIT] Profit Growth: {profit_growth * 100:.2f}%")

    # Expenses
    total_exp = metrics.get("total_expenses")
    exp_growth = metrics.get("expense_growth")
    exp_to_rev = metrics.get("expense_to_revenue_ratio")
    if total_exp is not None:
        lines.append(f"  [EXPENSES] Total Expenses: ${total_exp:,.2f}")
    if exp_growth is not None:
        lines.append(f"  [EXPENSES] Expense Growth: {exp_growth * 100:.2f}%")
    if exp_to_rev is not None:
        lines.append(f"  [EXPENSES] Expense/Revenue Ratio: {exp_to_rev * 100:.1f}%")

    # Specific expense items
    mktg = metrics.get("marketing_spend")
    if mktg is not None:
        lines.append(f"  [EXPENSES] Marketing Spend: ${mktg:,.2f}")
    mktg_roi = metrics.get("marketing_roi")
    if mktg_roi is not None:
        lines.append(f"  [EXPENSES] Marketing ROI: {mktg_roi:.2f}x")
    ship = metrics.get("shipping_costs")
    if ship is not None:
        lines.append(f"  [EXPENSES] Shipping Costs: ${ship:,.2f}")

    # Products / Mix
    for label, key in [
        ("Highest Revenue Product", "highest_revenue_product"),
        ("Lowest Revenue Product", "lowest_revenue_product"),
        ("Highest Selling Product", "highest_selling_product"),
        ("Lowest Selling Product", "lowest_selling_product"),
        ("Highest Profit Product", "highest_profit_product"),
        ("Lowest Profit Product", "lowest_profit_product"),
        ("Highest Margin Product", "highest_margin_product"),
        ("Highest Growth Product", "highest_growth_product"),
        ("Fastest Declining Product", "fastest_declining_product"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [PRODUCTS] {label}: {val}")

    # Product values
    for label, key in [
        ("Highest Revenue Product Value", "highest_revenue_product_value"),
        ("Lowest Revenue Product Value", "lowest_revenue_product_value"),
        ("Highest Profit Product Value", "highest_profit_product_value"),
        ("Lowest Profit Product Value", "lowest_profit_product_value"),
        ("Highest Selling Product Units", "highest_selling_product_units"),
        ("Lowest Selling Product Units", "lowest_selling_product_units"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [PRODUCTS] {label}: ${val:,.2f}" if "Value" in label or "Profit" in label else f"  [PRODUCTS] {label}: {val}")

    # Concentration scores
    for label, key in [
        ("Revenue Concentration Score", "revenue_concentration_score"),
        ("Profit Concentration Score", "profit_concentration_score"),
        ("Customer Concentration Score", "customer_concentration_score"),
        ("Supplier Concentration", "supplier_concentration"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [CONCENTRATION] {label}: {val:.4f}")

    # Customers
    for label, key in [
        ("Customer Count", "customer_count"),
        ("Customer Retention Rate", "customer_retention_rate"),
        ("Repeat Purchase Rate", "repeat_purchase_rate"),
        ("Avg Customer Value", "average_customer_value"),
        ("Largest Customer Rev Share", "largest_customer_revenue_share"),
    ]:
        val = metrics.get(key)
        if val is not None:
            if key in ("customer_retention_rate", "repeat_purchase_rate"):
                lines.append(f"  [CUSTOMERS] {label}: {val * 100:.1f}%")
            elif key == "largest_customer_revenue_share":
                lines.append(f"  [CUSTOMERS] {label}: {val * 100:.1f}%")
            else:
                lines.append(f"  [CUSTOMERS] {label}: {val}")

    # Employees
    for label, key in [
        ("Revenue per Employee", "revenue_per_employee"),
        ("Profit per Employee", "profit_per_employee"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [EMPLOYEES] {label}: ${val:,.2f}")

    # Cash Flow
    for label, key in [
        ("Operating Cash Flow", "operating_cashflow"),
        ("Free Cash Flow", "free_cashflow"),
        ("Cash Reserves", "cash_reserves"),
        ("Cash Burn Rate", "cash_burn_rate"),
        ("Cash Runway (months)", "cash_runway"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [CASH FLOW] {label}: {val}")

    # Inventory
    for label, key in [
        ("Inventory Value", "inventory_value"),
        ("Inventory Turnover", "inventory_turnover"),
        ("Avg Inventory Age (days)", "average_inventory_age"),
        ("Inventory Growth Rate", "inventory_growth_rate"),
        ("Inventory Carrying Cost", "inventory_carrying_cost"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [INVENTORY] {label}: {val}")

    # Receivables / Payables
    for label, key in [
        ("Accounts Receivable", "accounts_receivable"),
        ("Avg Collection Period (days)", "average_collection_period"),
        ("Accounts Payable", "accounts_payable"),
        ("Avg Payment Period (days)", "average_payment_period"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [AR/AP] {label}: {val}")

    # Ratios
    for label, key in [
        ("Return on Investment", "return_on_investment"),
        ("Return on Assets", "return_on_assets"),
        ("Return on Equity", "return_on_equity"),
        ("Debt/Equity Ratio", "debt_to_equity_ratio"),
        ("Current Ratio", "current_ratio"),
        ("Working Capital", "working_capital"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [RATIOS] {label}: {val}")

    # Returns / Discounts
    for label, key in [
        ("Return Rate", "return_rate"),
        ("Refund Rate", "refund_rate"),
        ("Discount Rate", "discount_rate"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [RETURNS] {label}: {val * 100:.2f}%")

    # Seasonal / Forecast
    for label, key in [
        ("Forecasted Revenue", "forecasted_revenue"),
        ("Forecasted Profit", "forecasted_profit"),
        ("Forecasted Demand", "forecasted_demand"),
        ("Peak Sales Month", "peak_sales_month"),
        ("Lowest Sales Month", "lowest_sales_month"),
        ("Seasonal Demand Score", "seasonal_demand_score"),
        ("Revenue Volatility", "revenue_volatility"),
        ("Profit Volatility", "profit_volatility"),
    ]:
        val = metrics.get(key)
        if val is not None:
            lines.append(f"  [FORECAST] {label}: {val}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("DATA COVERAGE NOTE: Only the metrics shown above are available.")
    lines.append("Metrics NOT listed above are NOT available in the current data.")
    lines.append("Use your expertise to INFER issues from available data even if")
    lines.append("some ideal metrics are missing. Partial data is better than no data.")
    lines.append("=" * 60)

    return "\n".join(lines)


def build_identify_issues_prompt(metrics: Dict[str, Any]) -> str:
    """
    Build the LLM prompt for identifying which financial issues
    exist given the current business metrics.
    Uses a directive, non-conservative approach that encourages
    the LLM to make intelligent inferences from available data.
    """
    metrics_summary = _summarize_metrics_for_issues(metrics)
    issues_str = "\n".join(f"  - {i}" for i in ALL_FINANCIAL_ISSUES)

    # Count available metrics
    available_count = sum(1 for k, v in metrics.items() if v is not None and not k.startswith("_"))

    # Determine what can be analyzed
    can_analyze = []
    if metrics.get("total_revenue") is not None:
        can_analyze.append("total revenue and revenue distribution across products")
    if metrics.get("highest_revenue_product") is not None:
        can_analyze.append("product-level performance (top/bottom products by revenue, sales, profit)")
    if metrics.get("revenue_concentration_score") is not None:
        can_analyze.append("revenue concentration risk across products")
    if metrics.get("customer_count") is not None:
        can_analyze.append("customer count and retention")
    if metrics.get("customer_concentration_score") is not None:
        can_analyze.append("customer concentration risk")
    if metrics.get("marketing_spend") is not None:
        can_analyze.append("marketing efficiency and ROI")
    if metrics.get("shipping_costs") is not None:
        can_analyze.append("shipping cost structure")
    if metrics.get("revenue_per_employee") is not None:
        can_analyze.append("employee productivity")
    if metrics.get("return_rate") is not None:
        can_analyze.append("return/refund rates")
    if metrics.get("inventory_value") is not None:
        can_analyze.append("inventory management")
    if metrics.get("accounts_receivable") is not None:
        can_analyze.append("accounts receivable/payable")

    can_analyze_str = "\n".join(f"  - ✓ {a}" for a in can_analyze)

    prompt = f"""You are an EXPERT forensic financial analyst. Your job is to identify financial leaks, inefficiencies, and profit-draining issues from available business metrics. You are AGGRESSIVE in finding issues — businesses lose money from subtle problems, and it's your job to surface them.

AVAILABLE METRICS ({available_count} metrics available):
{metrics_summary}

WHAT WE CAN ANALYZE WITH THE CURRENT DATA:
{can_analyze_str}

FULL LIST OF FINANCIAL ISSUES TO EVALUATE (check each one):
{issues_str}

CRITICAL INSTRUCTIONS:
1. Review EVERY potential financial issue against the available metrics.
2. For each issue:
   - If the data CLEARLY indicates the issue EXISTS (e.g., revenue is heavily concentrated in one product → revenue_concentration_risk), mark it as "exists".
   - If the data SUGGESTS the issue MAY be present (e.g., top and bottom products have very different performance → underperforming_products), mark it as "at_risk".
   - If the data ENABLES you to make a REASONABLE INFERENCE (e.g., we know the highest and lowest revenue products → we can assess product mix issues), do so.
   - Only mark "not_indicated" if the data truly provides NO insight into the issue.
3. BE BOLD, not conservative. It is BETTER to flag a potential issue as "at_risk" that turns out to be minor than to miss a real problem.
4. Use available data to make reasonable inferences. For example:
   - If we know the highest and lowest revenue products and their values, we CAN assess revenue_concentration_risk and underperforming_products.
   - If we know revenue and expense ratio, we CAN assess high_operating_costs.
   - If we know marketing spend and ROI, we CAN assess marketing efficiency.
   - If we know revenue per employee, we CAN assess productivity issues.
5. Rate severity realistically: "high" for issues that are clearly costing significant profit, "medium" for moderate concerns, "low" for early warning signs.

Return a JSON object with this exact structure:
{{
    "identified_issues": [
        {{
            "issue_id": "revenue_concentration_risk",
            "status": "exists",
            "severity": "high",
            "rationale": "Wireless Headphones generates $243,824 (23% of $1,060,830 total revenue), indicating heavy concentration risk in a single product.",
            "key_metrics": ["total_revenue", "highest_revenue_product", "highest_revenue_product_value", "revenue_concentration_score"],
            "context_for_report": "Product revenue is heavily concentrated in Wireless Headphones — analyze dependency risk and diversification opportunities"
        }}
    ],
    "no_issue_issues": [
        {{
            "issue_id": "declining_revenue",
            "reason": "Revenue is $1,060,830 for 2024-2025 with positive sales volume across 7 products. No trend data suggests decline."
        }}
    ]
}}

NOTES:
- Status must be "exists", "at_risk", or "not_indicated".
- Severity must be "high", "medium", or "low".
- Include issues where status is "exists" or "at_risk" in identified_issues.
- Include issues with status "not_indicated" in no_issue_issues with a reason.
- Return ONLY valid JSON, no other text.
"""

    return prompt


def identify_financial_issues(
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Use LLM to identify which financial issues and inefficiencies exist
    given the current business metrics. Falls back to heuristic analysis
    if LLM returns no identified issues.

    Args:
        metrics: Merged metrics dict from all filtered datasets.

    Returns:
        Dict with keys: identified_issues (list of issue dicts),
                        no_issue_issues (list of skipped issue dicts)
    """
    prompt = build_identify_issues_prompt(metrics)
    model = get_model()

    client = get_llm_client()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a forensic financial analyst who identifies real business issues from data. You return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=6000,
        )

        content = response.choices[0].message.content.strip()
        content = _strip_json_fences(content)
        result = _parse_json_response(content)

        # If LLM returned zero identified issues, fall through to heuristic
        if not result.get("identified_issues"):
            print("  LLM identified 0 issues — supplementing with heuristic analysis.")
            heuristic_result = heuristic_identify_issues(metrics)
            # Merge: keep LLM's no_issue_issues, add heuristic's identified issues
            result["identified_issues"] = heuristic_result.get("identified_issues", [])
            # Avoid duplicates in no_issue_issues
            existing_no_issue_ids = {i.get("issue_id") for i in result.get("no_issue_issues", [])}
            for hi in heuristic_result.get("no_issue_issues", []):
                if hi.get("issue_id") not in existing_no_issue_ids:
                    result.setdefault("no_issue_issues", []).append(hi)

        return result

    except Exception as e:
        print(f"  LLM issue identification failed ({e}), using heuristic fallback.")
        return heuristic_identify_issues(metrics)


# ──────────────────────────────────────────────────
# Step 2: Generate Financial Issue Report
# ──────────────────────────────────────────────────


def build_issue_report_prompt(
    metrics: Dict[str, Any],
    issue_id: str,
    severity: str,
    rationale: str,
    context: str,
    key_metrics: List[str],
) -> str:
    """
    Build the LLM prompt for generating a professional financial issue report.

    The report must contain:
    - Proper instructions on how to address the issue
    - Data backing the finding
    - Detailed explanation of the issue
    - Professional advice on solutions
    """
    metrics_summary = _summarize_metrics_for_issues(metrics)

    issue_display = issue_id.replace("_", " ").title()

    # Inline most relevant values directly into the prompt for easy reference
    rev_val = metrics.get('total_revenue', '$X')
    top_prod_val = metrics.get('highest_revenue_product_value', '$X')
    bot_prod_val = metrics.get('lowest_revenue_product_value', '$X')
    if isinstance(top_prod_val, (int, float)) and isinstance(bot_prod_val, (int, float)) and bot_prod_val > 0:
        ratio_display = f"{top_prod_val / bot_prod_val:.1f}x"
    else:
        ratio_display = "significantly"

    prompt = f"""You are a SENIOR FINANCIAL ANALYST writing a professional diagnostic report on a specific financial issue. Generate a DETAILED, DATA-RICH report on: "{issue_display}".

COMPANY METRICS — FULL CONTEXT:
{metrics_summary}

ISSUE DETAILS:
- Issue ID: {issue_id}
- Severity: {severity}
- Rationale: {rationale}
- Context: {context}

REPORT REQUIREMENTS — YOU MUST INCLUDE ALL OF THESE SECTIONS:

1. **Executive Summary** (2-3 paragraphs): Brief overview of the issue, its severity, why it matters, and the key takeaway for executives.

2. **Data & Evidence** (3-5 paragraphs): Present the SPECIFIC metrics and data that back this finding. Include ACTUAL NUMBERS from the company data. Compare figures, show ratios, highlight trends. Be precise — use dollar amounts and percentages.

3. **Detailed Analysis** (4-6 paragraphs): Explain WHY this issue is occurring, how it developed, and its QUANTIFIED impact on profitability. Connect the dots between different metrics. For example: "The top product generates ${top_prod_val} in revenue vs bottom product at ${bot_prod_val} — a {ratio_display} difference indicating severe product imbalance."

4. **Root Causes** (3-5 paragraphs): Identify the UNDERLYING causes based on the available data. Be specific about which metrics point to each root cause.

5. **Recommendations** (numbered list, 5-7 items): Provide CONCRETE, ACTIONABLE steps to address this issue. Each recommendation should be specific enough that the company could implement it. Include timelines and resource estimates where possible.

6. **Expected Impact** (2-3 paragraphs): QUANTIFY the potential financial benefit of resolving this issue. Use the company's actual revenue/profit figures as a baseline. Show your calculations.

CRITICAL RULES:
- Use the COMPANY'S ACTUAL NUMBERS from the metrics. Every claim must be backed by data.
- If certain data is missing, note that honestly and make conservative assumptions.
- Use a professional, executive-level tone.
- Be thorough — this report should be 2000+ words of substantive analysis.
- Include a boolean field "profitable_opportunity" — set to true if resolving this would improve profitability.

Return your response as a JSON object where:
- The TOP-LEVEL key is the report title: "{issue_display} Financial Issue Research"
- Each nested key is a section heading as specified above
- Each nested value is the full section content (can be multi-paragraph, use \n for line breaks)
- Include "profitable_opportunity" as a sibling of the section headings

Example format:
{{
    "{issue_display} Financial Issue Research": {{
        "profitable_opportunity": true,
        "Executive Summary": "This report analyzes ...",
        "Data & Evidence": "The company's metrics show ...",
        "Detailed Analysis": "Several factors contribute ...",
        "Root Causes": "The primary root causes ...",
        "Recommendations": "1. First action...\\n2. Second action...",
        "Expected Impact": "Resolving this issue could recover $X ..."
    }}
}}

Return ONLY valid JSON, no other text.
"""

    return prompt


def generate_issue_report(
    metrics: Dict[str, Any],
    issue_id: str,
    severity: str,
    rationale: str,
    context: str,
    key_metrics: List[str],
) -> Optional[Dict[str, Any]]:
    """
    Generate a single financial issue diagnostic report.

    Args:
        metrics: Full metrics dict.
        issue_id: Financial issue identifier (e.g., "declining_revenue").
        severity: Severity level ("high", "medium", "low").
        rationale: Brief rationale for why this issue was identified.
        context: Additional context for the report.
        key_metrics: List of metric keys relevant to this issue.

    Returns:
        Report dict in format {"Report Title": {"Section": "content", ...}},
        or None if no profitable opportunity exists.
    """
    prompt = build_issue_report_prompt(
        metrics, issue_id, severity, rationale, context, key_metrics
    )
    model = get_model()

    client = get_llm_client()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior financial analyst writing professional diagnostic reports. "
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=8000,
        )
    except Exception as e:
        print(f"    LLM API call failed for {issue_id}: {e}")
        return heuristic_generate_issue_report(
            metrics, issue_id, severity, rationale, context, key_metrics
        )

    try:
        content = response.choices[0].message.content.strip()
        content = _strip_json_fences(content)
        result = _parse_json_response(content)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"    LLM response parse failed for {issue_id}: {e}")
        return heuristic_generate_issue_report(
            metrics, issue_id, severity, rationale, context, key_metrics
        )

    # Check explicit profitable_opportunity boolean from LLM
    report_data = list(result.values())[0] if result else {}
    has_opportunity = report_data.get("profitable_opportunity", True)
    if not has_opportunity:
        return None

    # Remove the metadata field from sections
    if report_data:
        report_data.pop("profitable_opportunity", None)

    return result


# ──────────────────────────────────────────────────
# Heuristic fallback (no LLM)
# ──────────────────────────────────────────────────


def heuristic_identify_issues(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback: Identify financial issues by analyzing metric thresholds
    without LLM. Used when the LLM is unavailable or returns no results.

    Enhanced to also detect product portfolio, concentration, and
    efficiency issues from available metrics.
    """
    if not metrics:
        return {"identified_issues": [], "no_issue_issues": []}

    identified = []
    no_issue = []

    def safe_float(val, default=None):
        if val is None:
            return default
        try:
            fv = float(val)
            return fv
        except (TypeError, ValueError):
            return default

    # ── Revenue Issues ──
    rev = safe_float(metrics.get("total_revenue"))
    rev_growth = safe_float(metrics.get("revenue_growth"))
    rev_vol = safe_float(metrics.get("revenue_volatility"))

    if rev is not None and rev <= 0:
        identified.append({
            "issue_id": "declining_revenue",
            "status": "exists",
            "severity": "high",
            "rationale": f"Revenue is ${rev:,.2f}, indicating a critical decline.",
            "key_metrics": ["total_revenue", "revenue_growth"],
            "context_for_report": "Revenue is at zero or negative — immediate investigation needed.",
        })
    elif rev is not None and rev > 0:
        no_issue.append({
            "issue_id": "declining_revenue",
            "reason": f"Revenue is ${rev:,.2f} which is positive. No declining trend data available.",
        })

    if rev_growth is not None and rev_growth < -0.05:
        identified.append({
            "issue_id": "slowing_revenue_growth",
            "status": "exists" if rev_growth < -0.1 else "at_risk",
            "severity": "high" if rev_growth < -0.1 else "medium",
            "rationale": f"Revenue growth rate is {rev_growth * 100:.1f}%, indicating a decline.",
            "key_metrics": ["revenue_growth", "total_revenue"],
            "context_for_report": "Focus on historical revenue trends and growth trajectory.",
        })

    if rev_vol is not None and rev_vol > 0.3:
        identified.append({
            "issue_id": "volatile_revenue_streams",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Revenue volatility is {rev_vol:.4f}, indicating unstable income.",
            "key_metrics": ["revenue_volatility", "total_revenue"],
            "context_for_report": "Analyze revenue patterns for seasonal and cyclical components.",
        })

    # ── Product Portfolio Issues ──
    top_product = metrics.get("highest_revenue_product")
    top_product_rev = safe_float(metrics.get("highest_revenue_product_value"))
    bottom_product = metrics.get("lowest_revenue_product")
    bottom_product_rev = safe_float(metrics.get("lowest_revenue_product_value"))

    if top_product and bottom_product and top_product_rev and bottom_product_rev and top_product_rev > 0:
        ratio = top_product_rev / bottom_product_rev
        if ratio > 3 and rev is not None:
            # Heavy revenue concentration in top product
            top_share = top_product_rev / rev if rev > 0 else 0
            if top_share > 0.15:
                identified.append({
                    "issue_id": "revenue_concentration_risk",
                    "status": "exists",
                    "severity": "high" if top_share > 0.3 else "medium",
                    "rationale": f"Top product '{top_product}' generates ${top_product_rev:,.2f} ({top_share*100:.1f}% of total ${rev:,.2f}), indicating heavy concentration risk.",
                    "key_metrics": ["total_revenue", "highest_revenue_product", "highest_revenue_product_value", "revenue_concentration_score"],
                    "context_for_report": "Product revenue is heavily concentrated in one product — analyze dependency risk and diversification opportunities.",
                })

            # Underperforming products
            if bottom_product_rev < top_product_rev * 0.1:
                identified.append({
                    "issue_id": "underperforming_products",
                    "status": "exists",
                    "severity": "medium",
                    "rationale": f"'{bottom_product}' generates only ${bottom_product_rev:,.2f} ({bottom_product_rev/rev*100:.1f}% of revenue), while '{top_product}' generates ${top_product_rev:,.2f} ({top_share*100:.1f}%). The ratio is {ratio:.1f}x.",
                    "key_metrics": ["lowest_revenue_product", "lowest_revenue_product_value", "highest_revenue_product", "highest_revenue_product_value"],
                    "context_for_report": "Review bottom-performing products for potential consolidation, repricing, or discontinuation.",
                })

            # Inefficient product mix
            identified.append({
                "issue_id": "inefficient_product_mix",
                "status": "at_risk",
                "severity": "medium",
                "rationale": f"Product portfolio shows {ratio:.1f}x variance between top ('{top_product}') and bottom ('{bottom_product}') performers, suggesting suboptimal product mix.",
                "key_metrics": ["highest_revenue_product", "lowest_revenue_product", "highest_revenue_product_value", "lowest_revenue_product_value"],
                "context_for_report": "Analyze product mix and shift focus toward higher-performing products.",
            })

        # High margin / low volume check
        highest_margin = safe_float(metrics.get("highest_margin_product_value"))
        if highest_margin is not None:
            identified.append({
                "issue_id": "high_margin_low_volume_products",
                "status": "at_risk",
                "severity": "low",
                "rationale": f"Product margin data available — some products may have high margins but low volume, indicating untapped potential.",
                "key_metrics": ["highest_margin_product", "highest_margin_product_value"],
                "context_for_report": "Promote high-margin products to increase overall profitability.",
            })

    # ── Profit Issues ──
    gross_profit = safe_float(metrics.get("gross_profit"))
    net_profit = safe_float(metrics.get("net_profit"))
    gross_margin = safe_float(metrics.get("gross_margin"))
    net_margin = safe_float(metrics.get("net_margin"))
    margin_compression = safe_float(metrics.get("margin_compression_rate"))
    profit_growth = safe_float(metrics.get("profit_growth"))
    top_profit_product = metrics.get("highest_profit_product")
    top_profit_value = safe_float(metrics.get("highest_profit_product_value"))
    bottom_profit_value = safe_float(metrics.get("lowest_profit_product_value"))

    if net_profit is not None and net_profit <= 0:
        identified.append({
            "issue_id": "declining_profit",
            "status": "exists",
            "severity": "high",
            "rationale": f"Net profit is ${net_profit:,.2f}, indicating the business may be unprofitable.",
            "key_metrics": ["net_profit", "gross_profit", "total_revenue"],
            "context_for_report": "Profit is negative or zero — urgent cost and revenue analysis needed.",
        })

    if profit_growth is not None and profit_growth < -0.05:
        identified.append({
            "issue_id": "slowing_profit_growth",
            "status": "exists" if profit_growth < -0.1 else "at_risk",
            "severity": "high" if profit_growth < -0.1 else "medium",
            "rationale": f"Profit growth is {profit_growth * 100:.1f}%, indicating declining profitability.",
            "key_metrics": ["profit_growth", "net_profit", "gross_profit"],
            "context_for_report": "Analyze profit trend and identify cost or revenue factors.",
        })

    if gross_margin is not None and gross_margin < 0.2:
        identified.append({
            "issue_id": "margin_compression",
            "status": "exists",
            "severity": "high" if gross_margin < 0.1 else "medium",
            "rationale": f"Gross margin is {gross_margin * 100:.1f}%, below healthy threshold.",
            "key_metrics": ["gross_margin", "gross_profit", "total_revenue"],
            "context_for_report": "Analyze pricing, COGS, and product mix to identify margin pressure.",
        })

    if margin_compression is not None and margin_compression < -0.05:
        identified.append({
            "issue_id": "margin_compression",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Margin compression rate is {margin_compression * 100:.1f}%, margins are eroding.",
            "key_metrics": ["margin_compression_rate", "gross_margin", "net_margin"],
            "context_for_report": "Focus on margin trend and identify contributing factors.",
        })

    # Profit concentration risk
    if top_profit_value is not None and rev and rev > 0 and top_profit_value / rev > 0.1:
        identified.append({
            "issue_id": "profit_concentration_risk",
            "status": "exists",
            "severity": "high" if top_profit_value / rev > 0.2 else "medium",
            "rationale": f"'{top_profit_product}' generates ${top_profit_value:,.2f} in profit ({top_profit_value/rev*100:.1f}% of revenue), indicating profit concentration risk.",
            "key_metrics": ["highest_profit_product", "highest_profit_product_value", "lowest_profit_product", "lowest_profit_product_value"],
            "context_for_report": "Diversify profit sources to reduce dependency on top product.",
        })

    # ── Expense Issues ──
    total_exp = safe_float(metrics.get("total_expenses"))
    exp_growth = safe_float(metrics.get("expense_growth"))
    exp_to_rev = safe_float(metrics.get("expense_to_revenue_ratio"))

    if exp_growth is not None and exp_growth > 0.1:
        identified.append({
            "issue_id": "excessive_expense_growth",
            "status": "exists",
            "severity": "high" if exp_growth > 0.2 else "medium",
            "rationale": f"Expense growth is {exp_growth * 100:.1f}%, exceeding healthy levels.",
            "key_metrics": ["expense_growth", "total_expenses", "expense_to_revenue_ratio"],
            "context_for_report": "Break down expense categories to identify the fastest-growing costs.",
        })

    if rev_growth is not None and exp_growth is not None and exp_growth > rev_growth:
        identified.append({
            "issue_id": "expenses_growing_faster_than_revenue",
            "status": "exists",
            "severity": "high",
            "rationale": f"Expenses ({exp_growth * 100:.1f}%) are growing faster than revenue ({rev_growth * 100:.1f}%).",
            "key_metrics": ["expense_growth", "revenue_growth", "expense_to_revenue_ratio"],
            "context_for_report": "Analyze cost structure and identify expense categories that need control.",
        })

    if exp_to_rev is not None:
        if exp_to_rev > 0.8:
            identified.append({
                "issue_id": "high_operating_costs",
                "status": "exists",
                "severity": "high" if exp_to_rev > 0.9 else "medium",
                "rationale": f"Expense/revenue ratio is {exp_to_rev * 100:.1f}%, leaving thin margins.",
                "key_metrics": ["expense_to_revenue_ratio", "total_expenses", "total_revenue"],
                "context_for_report": "Review all expense categories for optimization opportunities.",
            })
        else:
            no_issue.append({
                "issue_id": "high_operating_costs",
                "reason": f"Expense/revenue ratio is {exp_to_rev * 100:.1f}%, which is well controlled.",
            })

    # ── Cash Flow Issues ──
    ocf = safe_float(metrics.get("operating_cashflow"))
    cash_reserves = safe_float(metrics.get("cash_reserves"))
    burn_rate = safe_float(metrics.get("cash_burn_rate"))
    cash_runway = safe_float(metrics.get("cash_runway"))

    if ocf is not None and ocf < 0:
        identified.append({
            "issue_id": "declining_cash_flow",
            "status": "exists",
            "severity": "high",
            "rationale": f"Operating cash flow is negative (${ocf:,.2f}), indicating cash drain.",
            "key_metrics": ["operating_cashflow", "net_cashflow", "cash_reserves"],
            "context_for_report": "Analyze cash conversion cycle and working capital management.",
        })

    if cash_reserves is not None:
        if rev and cash_reserves < rev * 0.05:
            identified.append({
                "issue_id": "low_cash_reserves",
                "status": "exists",
                "severity": "high",
                "rationale": f"Cash reserves are ${cash_reserves:,.2f} ({cash_reserves/rev*100:.1f}% of revenue), dangerously low.",
                "key_metrics": ["cash_reserves", "cash_burn_rate", "cash_runway"],
                "context_for_report": "Urgent cash conservation and liquidity management needed.",
            })

    if burn_rate is not None and burn_rate < 0:
        identified.append({
            "issue_id": "high_cash_burn_rate",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Cash burn rate is ${abs(burn_rate):,.2f}/month, depleting reserves.",
            "key_metrics": ["cash_burn_rate", "cash_reserves", "cash_runway"],
            "context_for_report": "Identify cash-draining activities and reduce burn rate.",
        })

    if cash_runway is not None and cash_runway < 6:
        identified.append({
            "issue_id": "high_cash_burn_rate",
            "status": "exists",
            "severity": "high" if cash_runway < 3 else "medium",
            "rationale": f"Cash runway is {cash_runway:.1f} months — at risk of running out.",
            "key_metrics": ["cash_runway", "cash_reserves", "cash_burn_rate"],
            "context_for_report": "Immediate cash flow planning and cost reduction needed.",
        })

    # ── Receivables Issues ──
    ar = safe_float(metrics.get("accounts_receivable"))
    avg_collection = safe_float(metrics.get("average_collection_period"))

    if avg_collection is not None and avg_collection > 45:
        identified.append({
            "issue_id": "increasing_accounts_receivable",
            "status": "exists",
            "severity": "high" if avg_collection > 90 else "medium",
            "rationale": f"Average collection period is {avg_collection:.0f} days, exceeding healthy 45 days.",
            "key_metrics": ["average_collection_period", "accounts_receivable"],
            "context_for_report": "Review credit terms, collection processes, and customer payment behavior.",
        })

    if avg_collection is not None and avg_collection > 60:
        identified.append({
            "issue_id": "poor_collection_efficiency",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Average collection period is {avg_collection:.0f} days, indicating weak collections.",
            "key_metrics": ["average_collection_period", "accounts_receivable"],
            "context_for_report": "Improve collection processes and consider invoice factoring.",
        })

    # ── Inventory Issues ──
    inv_turnover = safe_float(metrics.get("inventory_turnover"))
    inv_age = safe_float(metrics.get("average_inventory_age"))
    inv_growth = safe_float(metrics.get("inventory_growth_rate"))

    if inv_turnover is not None and inv_turnover < 4:
        identified.append({
            "issue_id": "declining_inventory_turnover",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Inventory turnover is {inv_turnover:.1f}x/year, indicating slow-moving stock.",
            "key_metrics": ["inventory_turnover", "average_inventory_age", "inventory_value"],
            "context_for_report": "Review inventory management practices and slow-moving items.",
        })

    if inv_age is not None and inv_age > 90:
        identified.append({
            "issue_id": "excess_inventory_levels",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Average inventory age is {inv_age:.0f} days, indicating overstocking.",
            "key_metrics": ["average_inventory_age", "inventory_turnover", "inventory_value"],
            "context_for_report": "Identify overstocked products and implement inventory reduction strategies.",
        })

    if inv_growth is not None and rev_growth is not None and inv_growth > rev_growth:
        identified.append({
            "issue_id": "inventory_growth_exceeding_sales_growth",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Inventory ({inv_growth * 100:.1f}%) growing faster than sales ({rev_growth * 100:.1f}%).",
            "key_metrics": ["inventory_growth_rate", "revenue_growth", "inventory_value"],
            "context_for_report": "Align inventory purchasing with actual sales trends.",
        })

    # ── Customer Issues ──
    cust_count = safe_float(metrics.get("customer_count"))
    ret_rate = safe_float(metrics.get("customer_retention_rate"))
    repeat_rate = safe_float(metrics.get("repeat_purchase_rate"))
    cust_concentration = safe_float(metrics.get("customer_concentration_score"))
    aov = safe_float(metrics.get("average_order_value"))
    refund_rate = safe_float(metrics.get("refund_rate"))
    discount_rate = safe_float(metrics.get("discount_rate"))

    if ret_rate is not None and ret_rate < 0.5:
        identified.append({
            "issue_id": "declining_customer_retention",
            "status": "exists",
            "severity": "high" if ret_rate < 0.3 else "medium",
            "rationale": f"Customer retention rate is {ret_rate * 100:.1f}%, indicating churn issues.",
            "key_metrics": ["customer_retention_rate", "repeat_purchase_rate", "customer_count"],
            "context_for_report": "Investigate customer satisfaction, competitive offers, and retention strategies.",
        })

    if repeat_rate is not None and repeat_rate < 0.3:
        identified.append({
            "issue_id": "declining_repeat_purchase_rate",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Repeat purchase rate is {repeat_rate * 100:.1f}%, most customers are one-time buyers.",
            "key_metrics": ["repeat_purchase_rate", "customer_retention_rate", "average_customer_value"],
            "context_for_report": "Develop customer loyalty programs and post-purchase engagement.",
        })

    if aov is not None and aov < 50:
        identified.append({
            "issue_id": "declining_average_order_value",
            "status": "at_risk",
            "severity": "low",
            "rationale": f"Average order value is ${aov:.2f}, consider upselling opportunities.",
            "key_metrics": ["average_order_value"],
            "context_for_report": "Explore bundling, cross-selling, and volume discounts to increase AOV.",
        })

    if refund_rate is not None:
        if refund_rate > 0.1:
            identified.append({
                "issue_id": "high_refund_rates",
                "status": "exists",
                "severity": "medium",
                "rationale": f"Refund rate is {refund_rate * 100:.1f}%, indicating product or service issues.",
                "key_metrics": ["refund_rate", "return_rate"],
                "context_for_report": "Analyze refund reasons and address product quality or expectation gaps.",
            })
        else:
            no_issue.append({
                "issue_id": "high_refund_rates",
                "reason": f"Refund/return rate is {refund_rate * 100:.2f}%, which is low and healthy.",
            })

    if discount_rate is not None and discount_rate > 0.15:
        identified.append({
            "issue_id": "excessive_discounting",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Discount rate is {discount_rate * 100:.1f}%, eroding margins.",
            "key_metrics": ["discount_rate", "gross_margin", "net_margin"],
            "context_for_report": "Review discount strategy and implement margin-aware pricing.",
        })

    # ── Customer Concentration ──
    if cust_concentration is not None and cust_concentration > 0.3:
        identified.append({
            "issue_id": "customer_concentration_risk",
            "status": "exists",
            "severity": "high" if cust_concentration > 0.5 else "medium",
            "rationale": f"Customer concentration score is {cust_concentration:.4f}, showing dependency on few customers.",
            "key_metrics": ["customer_concentration_score", "largest_customer_revenue_share"],
            "context_for_report": "Diversify customer base to reduce risk from losing key accounts.",
        })

    # ── Customer Dependency (fallback if we have customer count but no concentration) ──
    if cust_count is not None and cust_count < 5:
        identified.append({
            "issue_id": "customer_dependency_risk",
            "status": "at_risk",
            "severity": "medium",
            "rationale": f"Only {int(cust_count)} customers identified — high dependency on a small customer base.",
            "key_metrics": ["customer_count"],
            "context_for_report": "Diversify customer base to reduce dependency on few accounts.",
        })

    # ── Supplier Issues ──
    sup_concentration = safe_float(metrics.get("supplier_concentration"))
    if sup_concentration is not None and sup_concentration > 0.3:
        identified.append({
            "issue_id": "supplier_concentration_risk",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Supplier concentration score is {sup_concentration:.4f}, risky supply chain dependency.",
            "key_metrics": ["supplier_concentration", "largest_supplier_spend"],
            "context_for_report": "Identify alternative suppliers to reduce dependency on few sources.",
        })

    # ── Supplier Dependency ──
    supp_dep = safe_float(metrics.get("supplier_dependency_score"))
    if supp_dep is not None and supp_dep > 0.5:
        identified.append({
            "issue_id": "supplier_dependency_risk",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Supplier dependency score is {supp_dep:.4f}, indicating heavy reliance on a single supplier.",
            "key_metrics": ["supplier_dependency_score", "largest_supplier_spend"],
            "context_for_report": "Diversify supplier base to mitigate supply chain risk.",
        })

    # ── Employee Issues ──
    rev_per_emp = safe_float(metrics.get("revenue_per_employee"))
    profit_per_emp = safe_float(metrics.get("profit_per_employee"))

    if rev_per_emp is not None and rev_per_emp < 1000:
        identified.append({
            "issue_id": "declining_revenue_per_employee",
            "status": "at_risk",
            "severity": "medium",
            "rationale": f"Revenue per employee is ${rev_per_emp:,.2f}, indicating low productivity.",
            "key_metrics": ["revenue_per_employee", "profit_per_employee"],
            "context_for_report": "Review workforce efficiency and consider automation opportunities.",
        })

    if profit_per_emp is not None and profit_per_emp < 500:
        identified.append({
            "issue_id": "declining_profit_per_employee",
            "status": "at_risk",
            "severity": "medium",
            "rationale": f"Profit per employee is ${profit_per_emp:,.2f}, suggesting thin margins per employee.",
            "key_metrics": ["profit_per_employee", "revenue_per_employee"],
            "context_for_report": "Evaluate employee productivity and cost structure.",
        })

    # ── Product Mix (Product-based concentration) ──
    highest_margin = metrics.get("highest_margin_product")
    highest_rev = metrics.get("highest_revenue_product")

    if highest_margin and highest_rev and highest_margin != highest_rev:
        identified.append({
            "issue_id": "inefficient_product_mix",
            "status": "at_risk",
            "severity": "low",
            "rationale": "Top revenue and top margin products differ — opportunity to optimize product mix.",
            "key_metrics": ["highest_margin_product", "highest_revenue_product", "product_profitability_score"],
            "context_for_report": "Analyze product mix and shift focus toward higher-margin products.",
        })

    # ── Ratio & Health Issues ──
    roa = safe_float(metrics.get("return_on_assets"))
    roe = safe_float(metrics.get("return_on_equity"))
    roi = safe_float(metrics.get("return_on_investment"))
    de_ratio = safe_float(metrics.get("debt_to_equity_ratio"))
    working_cap = safe_float(metrics.get("working_capital"))
    profit_vol = safe_float(metrics.get("profit_volatility"))

    if roi is not None and roi < 0.05:
        identified.append({
            "issue_id": "poor_return_on_investment",
            "status": "exists" if roi < 0 else "at_risk",
            "severity": "high" if roi < 0 else "medium",
            "rationale": f"Return on investment is {roi * 100:.1f}%, below healthy threshold.",
            "key_metrics": ["return_on_investment", "net_profit"],
            "context_for_report": "Evaluate capital allocation and investment efficiency.",
        })

    if roa is not None and roa < 0.05:
        identified.append({
            "issue_id": "poor_return_on_assets",
            "status": "at_risk",
            "severity": "medium",
            "rationale": f"Return on assets is {roa * 100:.1f}%, indicating weak asset utilization.",
            "key_metrics": ["return_on_assets", "net_profit"],
            "context_for_report": "Review asset utilization and identify underperforming assets.",
        })

    if roe is not None and roe < 0.08:
        identified.append({
            "issue_id": "poor_return_on_equity",
            "status": "at_risk",
            "severity": "medium",
            "rationale": f"Return on equity is {roe * 100:.1f}%, below typical investor expectations.",
            "key_metrics": ["return_on_equity", "net_profit"],
            "context_for_report": "Analyze capital structure and profitability drivers.",
        })

    if de_ratio is not None and de_ratio > 2.0:
        identified.append({
            "issue_id": "increasing_financial_risk",
            "status": "exists",
            "severity": "high" if de_ratio > 3.0 else "medium",
            "rationale": f"Debt-to-equity ratio is {de_ratio:.2f}, indicating high leverage.",
            "key_metrics": ["debt_to_equity_ratio", "current_ratio", "working_capital"],
            "context_for_report": "Review debt structure and consider deleveraging strategies.",
        })

    if profit_vol is not None and profit_vol > 0.5:
        identified.append({
            "issue_id": "volatile_profitability",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Profit volatility is {profit_vol:.4f}, indicating unstable earnings.",
            "key_metrics": ["profit_volatility", "profit_growth", "net_profit"],
            "context_for_report": "Stabilize profit through cost control and revenue diversification.",
        })

    # ── Marketing Issues ──
    mktg_roi = safe_float(metrics.get("marketing_roi"))
    mktg_spend = safe_float(metrics.get("marketing_spend"))

    if mktg_roi is not None and mktg_roi < 2:
        identified.append({
            "issue_id": "inefficient_resource_allocation",
            "status": "exists",
            "severity": "medium",
            "rationale": f"Marketing ROI is only {mktg_roi:.2f}x, indicating poor marketing efficiency.",
            "key_metrics": ["marketing_roi", "marketing_spend"],
            "context_for_report": "Review marketing campaigns and reallocate budget to higher-performing channels.",
        })

    if not identified:
        no_issue.append({
            "issue_id": "general_financial_health",
            "reason": "No significant issues detected from available metrics — financial position appears healthy.",
        })

    # Remove any duplicate issue_ids (keep first occurrence)
    seen_ids = set()
    deduped = []
    for issue in identified:
        iid = issue.get("issue_id")
        if iid not in seen_ids:
            seen_ids.add(iid)
            deduped.append(issue)
        else:
            # Merge rationale if duplicate
            for existing in deduped:
                if existing.get("issue_id") == iid:
                    existing["rationale"] += " " + issue.get("rationale", "")
                    severity_map = {"low": 0, "medium": 1, "high": 2}
                    rev_map = {0: "low", 1: "medium", 2: "high"}
                    max_val = max(
                        severity_map.get(existing.get("severity", "low"), 0),
                        severity_map.get(issue.get("severity", "low"), 0)
                    )
                    existing["severity"] = rev_map[max_val]
                    existing["key_metrics"] = list(set(existing.get("key_metrics", []) + issue.get("key_metrics", [])))
                    break

    return {
        "identified_issues": deduped,
        "no_issue_issues": no_issue,
    }


def heuristic_generate_issue_report(
    metrics: Dict[str, Any],
    issue_id: str,
    severity: str,
    rationale: str,
    context: str,
    key_metrics: List[str],
) -> Dict[str, Any]:
    """
    Fallback: Generate a basic issue report template from metrics without LLM.
    Enhanced to provide more useful analysis from available data.
    """
    issue_display = issue_id.replace("_", " ").title()

    # Build data section with all relevant metrics
    relevant = {}
    for k, v in metrics.items():
        if v is not None and not k.startswith("_") and (k in key_metrics or k in [
            "total_revenue", "total_units_sold", "expense_to_revenue_ratio",
            "marketing_spend", "shipping_costs", "return_rate",
            "revenue_per_employee", "profit_per_employee", "marketing_roi",
        ]):
            relevant[k] = v

    data_lines = ["Key metrics available for this analysis:"]
    for key, val in sorted(relevant.items()):
        if isinstance(val, float):
            if "rate" in key or "margin" in key or "ratio" in key:
                data_lines.append(f"  - {key}: {val*100:.2f}%")
            elif "revenue" in key or "profit" in key or "cost" in key or "spend" in key or "value" in key:
                data_lines.append(f"  - {key}: ${val:,.2f}")
            else:
                data_lines.append(f"  - {key}: {val:,.2f}")
        else:
            data_lines.append(f"  - {key}: {val}")
    data_section = "\n".join(data_lines)

    report_title = f"{issue_display} Financial Issue Research"

    return {
        report_title: {
            "Executive Summary": (
                f"Financial issue identified: {issue_display}. "
                f"Severity level: {severity.upper()}. "
                f"{rationale}"
            ),
            "Data & Evidence": data_section,
            "Detailed Analysis": (
                f"Heuristic analysis for {issue_display}.\n\n"
                f"Severity: {severity}\n\n"
                f"Rationale: {rationale}\n\n"
                f"Context: {context}\n\n"
                f"This is a heuristic-generated analysis. {len(relevant)} relevant metrics were found. "
                f"For a more detailed analysis with specific recommendations and quantified impact, "
                f"re-run with LLM integration enabled."
            ),
            "Root Causes": (
                f"Based on heuristic analysis of available metrics for {issue_display}:\n\n"
                f"Primary indicators: {', '.join(relevant.keys()) if relevant else 'limited data available'}\n\n"
                f"Recommend deeper analysis with LLM for comprehensive root cause identification."
            ),
            "Recommendations": (
                f"1. Investigate {issue_display.replace('_', ' ')} thoroughly.\n"
                f"2. Review relevant metrics: {', '.join(key_metrics)}.\n"
                f"3. Monitor trends and implement corrective measures.\n"
                f"4. Consult financial advisor for detailed action plan.\n"
                f"5. Set up automated alerts for early detection of worsening conditions."
            ),
            "Expected Impact": (
                f"Heuristic estimation for {issue_display}:\n\n"
                f"Impact severity: {severity.upper()}\n\n"
                f"Note: LLM analysis required for precise quantification. "
                f"Based on available data, resolving this issue could meaningfully "
                f"improve the company's financial position."
            ),
            "_heuristic_fallback": "true",
        }
    }
