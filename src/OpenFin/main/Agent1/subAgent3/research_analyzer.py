"""
research_analyzer.py
Key objective: Use LLM (via OpenRouter) to:
  1. Identify which research topics are worth pursuing based on available metrics
  2. Generate professional research insight reports combining metrics + web search results

Uses OpenRouter API (OpenAI-compatible). Configure via environment variables:
    OPENAI_API_KEY  - OpenRouter API key (required)
    OPENAI_BASE_URL - Base URL (default: https://openrouter.ai/api/v1)
    LLM_MODEL       - Model name (default: openai/gpt-oss-120b:free)
"""
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from main.llm_client import get_llm_client, get_model

# ── All known research topics (from specs.md) ───────

ALL_RESEARCH_TOPICS = [
    "alternative_suppliers",
    "lower_supplier_pricing",
    "better_supplier_terms",
    "supplier_dependency_risks",
    "emerging_high_demand_products",
    "declining_product_categories",
    "seasonal_market_trends",
    "competitor_pricing_trends",
    "industry_profit_margin_benchmarks",
    "industry_expense_benchmarks",
    "inventory_optimization_opportunities",
    "pricing_optimization_opportunities",
    "customer_retention_opportunities",
    "revenue_diversification_opportunities",
    "cost_reduction_opportunities",
    "automation_opportunities",
    "operational_efficiency_improvements",
    "cash_flow_optimization_strategies",
    "new_sales_channel_opportunities",
    "geographic_expansion_opportunities",
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
# Step 1: Identify Research Topics
# ──────────────────────────────────────────────────

def build_identify_topics_prompt(metrics: Dict[str, Any]) -> str:
    """
    Build the LLM prompt for identifying which research topics are worth
    pursuing given the current business metrics.
    """
    # Summarize key metrics for the LLM
    metrics_summary = _summarize_metrics(metrics)
    topics_str = "\n".join(f"  - {t}" for t in ALL_RESEARCH_TOPICS)

    prompt = f"""You are a strategic business consultant specializing in profitability improvement. Given the following business metrics, identify which research topics would be MOST valuable to investigate for increasing profit.

CURRENT BUSINESS METRICS:
{metrics_summary}

AVAILABLE RESEARCH TOPICS:
{topics_str}

INSTRUCTIONS:
1. Review the metrics carefully. Focus on identifying data-backed opportunities.
2. For each topic, determine if the available metrics support investigating it.
3. Prioritize topics that could directly increase profit or reduce costs.
4. Return a JSON object with this exact structure:

{{
    "prioritized_topics": [
        {{
            "topic": "pricing_optimization_opportunities",
            "priority": "high",
            "rationale": "Brief explanation of why this topic is relevant given the metrics",
            "context_for_search": "specific products, customers, or data points to focus the search on"
        }}
    ],
    "product_categories": "comma-separated list of main product categories from the data",
    "industry": "the most specific industry classification for this business",
    "skipped_topics": [
        {{
            "topic": "alternative_suppliers",
            "reason": "No supplier data available in metrics"
        }}
    ]
}}

NOTES:
- Priority should be "high", "medium", or "low".
- Only include topics where the metrics provide sufficient context.
- If no topics have sufficient data, return an empty prioritized_topics list.
- Return ONLY valid JSON, no other text.
"""
    return prompt


def _summarize_metrics(metrics: Dict[str, Any]) -> str:
    """
    Build a concise summary of available metrics for the LLM prompt.
    """
    if not metrics:
        return "No metrics available."

    lines = []
    # Financial overview
    rev = metrics.get("total_revenue")
    profit = metrics.get("gross_profit") or metrics.get("net_profit")
    margin = metrics.get("gross_margin")
    if rev is not None:
        lines.append(f"  Total Revenue: ${rev:,.2f}")
    if profit is not None:
        lines.append(f"  Gross Profit: ${profit:,.2f}")
    if margin is not None:
        lines.append(f"  Gross Margin: {margin * 100:.1f}%")
    lines.append("")

    # Products
    for key, label in [
        ("highest_revenue_product", "Top revenue product"),
        ("lowest_revenue_product", "Lowest revenue product"),
        ("highest_profit_product", "Top profit product"),
        ("lowest_profit_product", "Lowest profit product"),
        ("highest_margin_product", "Highest margin product"),
        ("lowest_margin_product", "Lowest margin product"),
        ("highest_selling_product", "Highest selling product (units)"),
        ("fastest_moving_product", "Fastest moving product"),
        ("slowest_moving_product", "Slowest moving product"),
    ]:
        val = metrics.get(key)
        if val:
            lines.append(f"  {label}: {val}")

    # Customers & Suppliers
    cust_count = metrics.get("customer_count")
    supplier_count = metrics.get("supplier_count")
    if cust_count is not None:
        lines.append(f"  Customer count: {cust_count}")
    if supplier_count is not None:
        lines.append(f"  Supplier count: {supplier_count}")

    # Key ratios
    for key, label in [
        ("return_rate", "Return rate"),
        ("expense_to_revenue_ratio", "Expense/revenue ratio"),
        ("marketing_roi", "Marketing ROI"),
        ("marketing_spend", "Marketing spend"),
        ("shipping_costs", "Shipping costs"),
        ("revenue_per_employee", "Revenue/employee"),
        ("profit_per_employee", "Profit/employee"),
        ("average_order_value", "Average order value"),
    ]:
        val = metrics.get(key)
        if val is not None:
            if isinstance(val, float) and val < 1 and "rate" in key:
                lines.append(f"  {label}: {val * 100:.2f}%")
            elif isinstance(val, float):
                lines.append(f"  {label}: ${val:,.2f}")
            else:
                lines.append(f"  {label}: {val}")

    return "\n".join(lines)


def identify_research_topics(
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Use LLM to identify which research topics are worth pursuing.
    Falls back to heuristic if LLM is unavailable.

    Args:
        metrics: Merged metrics dict from all filtered datasets.

    Returns:
        Dict with keys: prioritized_topics, product_categories, industry, skipped_topics
    """
    try:
        prompt = build_identify_topics_prompt(metrics)
        model = get_model()

        client = get_llm_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strategic business consultant. You return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )

        content = response.choices[0].message.content.strip()
        content = _strip_json_fences(content)
        result = _parse_json_response(content)

        if not result.get("prioritized_topics"):
            print("  LLM returned empty topics — using heuristic fallback.")
            return heuristic_identify_topics(metrics)
        return result

    except Exception as e:
        print(f"  LLM topic identification failed ({e}), using heuristic fallback.")
        return heuristic_identify_topics(metrics)


# ──────────────────────────────────────────────────
# Heuristic fallback: topic identification (no LLM)
# ──────────────────────────────────────────────────

def heuristic_identify_topics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback: Identify relevant research topics based on available metrics
    without LLM. Selects default high-value topics from the specs list.
    """
    prioritized = []

    # Always include these core profit-improvement topics
    core_topics = [
        "pricing_optimization_opportunities",
        "cost_reduction_opportunities",
        "inventory_optimization_opportunities",
        "customer_retention_opportunities",
        "revenue_diversification_opportunities",
        "operational_efficiency_improvements",
    ]

    for topic in core_topics:
        display = topic.replace("_", " ").title()
        prioritized.append({
            "topic": topic,
            "priority": "medium",
            "rationale": f"Core profit-improvement research topic: {display}",
            "context_for_search": f"{display} strategies for small business",
        })

    # Add supplier topics if supplier data present
    if metrics.get("supplier_count") is not None:
        supplier_topics = [
            "alternative_suppliers",
            "lower_supplier_pricing",
        ]
        for topic in supplier_topics:
            display = topic.replace("_", " ").title()
            prioritized.append({
                "topic": topic,
                "priority": "medium",
                "rationale": f"Supplier data available — research {display}",
                "context_for_search": f"{display} for consumer electronics",
            })

    # Add market trend topics
    market_topics = [
        "competitor_pricing_trends",
        "industry_profit_margin_benchmarks",
        "new_sales_channel_opportunities",
    ]
    for topic in market_topics:
        display = topic.replace("_", " ").title()
        prioritized.append({
            "topic": topic,
            "priority": "medium",
            "rationale": f"Market research topic: {display}",
            "context_for_search": f"{display} {datetime.now().year}",
        })

    # Add automation if employee metrics present
    if metrics.get("revenue_per_employee") is not None:
        prioritized.append({
            "topic": "automation_opportunities",
            "priority": "medium",
            "rationale": "Employee productivity data available — explore automation",
            "context_for_search": "automation tools for small business operations",
        })

    return {
        "prioritized_topics": prioritized,
        "product_categories": "consumer electronics",
        "industry": "consumer electronics retail",
        "skipped_topics": [],
    }


# ──────────────────────────────────────────────────
# Step 2: Generate Research Report
# ──────────────────────────────────────────────────

def build_research_report_prompt(
    metrics: Dict[str, Any],
    topic: str,
    search_results: Optional[Dict[str, Any]],
    product_categories: str,
    industry: str,
) -> str:
    """
    Build the LLM prompt for generating a research insight report
    combining business metrics with web search findings.
    """
    metrics_summary = _summarize_metrics(metrics)

    # Format search results
    if search_results and search_results.get("answer"):
        search_summary = search_results["answer"][:1500]
        search_sources = ""
        for i, r in enumerate(search_results.get("results", [])[:3]):
            search_sources += f"  [{i + 1}] {r.get('url', '')}\n"
            search_sources += f"      {r.get('content', '')[:250]}\n"
    else:
        search_summary = "(No web search results available — provide analysis based on metrics alone.)"
        search_sources = ""

    topic_display = topic.replace("_", " ").title()

    prompt = f"""You are a strategic business consultant writing a research insight report on profitability improvement. Generate a report on "{topic_display}".

COMPANY CONTEXT:
- Industry: {industry}
- Product Categories: {product_categories}

CURRENT METRICS:
{metrics_summary}

WEB RESEARCH FINDINGS:
Summary: {search_summary}
Sources:
{search_sources}

INSTRUCTIONS:
1. Write a professional research insight report focused on HOW the company can improve profitability through this specific area.
2. Base your analysis on BOTH the company's actual metrics AND the web research findings.
3. The report MUST include these sections:
   - **Executive Summary**: Key finding and its profit impact potential
   - **Current State**: The company's current position based on their metrics
   - **Market Research**: What the internet research reveals about best practices / benchmarks / alternatives
   - **Gap Analysis**: How the company compares to market benchmarks or best practices
   - **Recommendations**: Concrete, actionable steps the company should take
   - **Estimated Impact**: Quantify the potential profit impact if possible (use the actual metrics to estimate)
4. Be specific. Use the company's actual numbers. Don't be vague.
5. Include a boolean field `"profitable_opportunity"` set to `true` if the research reveals a clear profit improvement opportunity, or `false` if no meaningful opportunity exists.
6. If profitable_opportunity is false, still provide a complete report but set the field accordingly.

Return your response as a JSON object where:
- The top-level key is the report title (use "{topic_display} Research")
- Each nested key is a section heading
- Each nested value is the section content
- Include the `profitable_opportunity` boolean as a sibling of the section headings

Example format:
{{
    "{topic_display} Research": {{
        "profitable_opportunity": true,
        "Executive Summary": "...",
        "Current State": "...",
        "Market Research": "...",
        "Gap Analysis": "...",
        "Recommendations": "...",
        "Estimated Impact": "..."
    }}
}}

Return ONLY valid JSON, no other text.
"""
    return prompt


def heuristic_generate_research_report(
    metrics: Dict[str, Any],
    topic: str,
    product_categories: str = "consumer electronics",
    industry: str = "consumer electronics retail",
) -> Dict[str, Any]:
    """
    Fallback: Generate a basic research insight report from metrics without LLM.
    """
    topic_display = topic.replace("_", " ").title()
    report_title = f"{topic_display} Research"

    # Collect relevant metrics for this report
    relevant = {}
    for k, v in metrics.items():
        if v is not None and not k.startswith("_"):
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

    return {
        report_title: {
            "Executive Summary": (
                f"Research insight report on {topic_display}. "
                f"This report aims to identify profit improvement opportunities "
                f"for a {industry} business in the {product_categories} category. "
                f"Based on available metrics, {topic.replace('_', ' ')} represents "
                f"a potential area for profit enhancement."
            ),
            "Current State": (
                f"The company currently operates in the {industry} sector "
                f"with products in the {product_categories} category. "
                f"{data_section}\n\n"
                f"This heuristic analysis is based on {len(relevant)} available metrics. "
                f"For a more detailed analysis with specific benchmarks and quantified impact, "
                f"re-run with LLM integration enabled."
            ),
            "Market Research": (
                f"Research on {topic_display} in the {industry} sector:\n\n"
                f"Best practices and industry benchmarks for {topic.replace('_', ' ')} "
                f"vary by sector, but key considerations include competitive positioning, "
                f"cost structure optimization, and market trend alignment.\n\n"
                f"Note: Detailed online research data is not available in heuristic mode. "
                f"Enable LLM and Tavily API integration for comprehensive market research findings."
            ),
            "Gap Analysis": (
                f"Comparing the company's {len(relevant)} available metrics against "
                f"typical {industry} benchmarks:\n\n"
                f"A full gap analysis requires LLM-powered comparison of specific metrics "
                f"against industry benchmarks. Based on available data, this topic "
                f"represents a meaningful opportunity for profit improvement "
                f"through {topic.replace('_', ' ')}."
            ),
            "Recommendations": (
                f"1. Research {topic_display} best practices in the {industry} sector.\n"
                f"2. Benchmark current metrics against industry standards.\n"
                f"3. Identify specific {topic.replace('_', ' ')} actions applicable to the business.\n"
                f"4. Develop an implementation plan with measurable targets.\n"
                f"5. Monitor results and adjust strategy based on outcomes."
            ),
            "Estimated Impact": (
                f"Heuristic estimation for {topic_display}:\n\n"
                f"Impact potential: MEDIUM\n\n"
                f"Note: Precise quantification requires LLM analysis. "
                f"Based on available metrics, implementing {topic.replace('_', ' ')} "
                f"improvements could meaningfully enhance profitability."
            ),
        }
    }


def generate_research_report(
    metrics: Dict[str, Any],
    topic: str,
    search_results: Optional[Dict[str, Any]],
    product_categories: str = "consumer electronics",
    industry: str = "consumer electronics retail",
) -> Optional[Dict[str, Any]]:
    """
    Generate a single research insight report. Falls back to heuristic
    if LLM is unavailable.

    Args:
        metrics: Full metrics dict.
        topic: Research topic identifier (e.g., "pricing_optimization_opportunities").
        search_results: Tavily search result dict for this topic.
        product_categories: Product category context.
        industry: Industry name.

    Returns:
        Report dict in format {"Report Title": {"Section": "content", ...}},
        or None if no profitable solution found.
    """
    try:
        prompt = build_research_report_prompt(
            metrics, topic, search_results, product_categories, industry
        )
        model = get_model()

        client = get_llm_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strategic business consultant writing research insight reports. "
                        "You return only valid JSON. If no profitable opportunity exists, "
                        "include a section clearly stating that."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=6000,
        )

        content = response.choices[0].message.content.strip()
        content = _strip_json_fences(content)
        result = _parse_json_response(content)

        # Check explicit profitable_opportunity boolean from LLM
        report_data = list(result.values())[0] if result else {}
        has_opportunity = report_data.get("profitable_opportunity", True)
        if not has_opportunity:
            return None

        # Remove the metadata field from sections (it's not a report section)
        if report_data:
            report_data.pop("profitable_opportunity", None)

        return result

    except Exception as e:
        print(f"    LLM report generation failed ({e}), using heuristic fallback.")
        return heuristic_generate_research_report(
            metrics, topic, product_categories, industry
        )
