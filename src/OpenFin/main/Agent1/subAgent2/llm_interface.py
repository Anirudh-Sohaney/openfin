"""
llm_interface.py
Key objective: Interface with an LLM via OpenRouter API to:
  1. Identify which financial reports can be generated from available metrics
  2. Generate detailed reports with Data, Analysis, and Conclusion sections

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
from typing import Dict, List, Any, Optional
from main.llm_client import get_llm_client, get_model

# ── Known report types (from specs.md) ────────────

KNOWN_REPORT_TYPES = [
    "Executive Financial Summary Report",
    "Revenue Report",
    "Sales Report",
    "Profit & Loss Report",
    "Expense Report",
    "Cash Flow Report",
    "Inventory Report",
    "Product Performance Report",
    "Supplier Report",
    "Customer Report",
    "Accounts Receivable Report",
    "Accounts Payable Report",
    "Payroll Report",
    "Financial Health Report",
    "Business Growth Report",
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
        # Try to extract JSON block
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"LLM returned invalid JSON: {content[:500]}")


# ──────────────────────────────────────────────────
# Report Identification
# ──────────────────────────────────────────────────

def build_identify_reports_prompt(
    all_metrics: List[Dict[str, Any]],
    existing_reports: List[str],
) -> str:
    """
    Build the LLM prompt for identifying which reports can be generated
    from the currently available metrics.
    """
    # Summarize available metrics across all filtered datasets
    metrics_summary = _summarize_metrics(all_metrics)

    known_reports_str = "\n".join(f"  - {r}" for r in KNOWN_REPORT_TYPES)
    existing_str = "\n".join(f"  - {r}" for r in existing_reports) if existing_reports else "  (none)"

    prompt = f"""You are a senior financial analyst. Given the following available metrics, determine which financial reports CAN be generated.

AVAILABLE METRICS SUMMARY:
{metrics_summary}

EXISTING REPORTS (already generated, skip these unless metrics changed):
{existing_str}

KNOWN REPORT TYPES:
{known_reports_str}

INSTRUCTIONS:
1. Review the available metrics carefully.
2. For each known report type, determine if enough data exists to generate it.
3. For each report you identify as possible, list the specific metric keys needed.
4. Return a JSON object with this exact structure:

{{
    "possible_reports": [
        {{
            "report_name": "Revenue Report",
            "required_metrics": ["total_revenue", "yearly_revenue", "revenue_growth"],
            "confidence": "high",
            "rationale": "Brief explanation of why this report can be generated"
        }}
    ],
    "unavailable_reports": [
        {{
            "report_name": "Payroll Report",
            "reason": "No employee count or payroll expense metrics available"
        }}
    ]
}}

NOTES:
- Only suggest reports that have sufficient metrics to be meaningful.
- Use "high", "medium", or "low" for confidence.
- Be thorough but realistic about what can be generated.
- Return ONLY valid JSON, no other text.
"""
    return prompt


def _summarize_metrics(all_metrics: List[Dict[str, Any]]) -> str:
    """
    Build a concise summary of available metrics for the LLM prompt.

    Groups metrics by category and shows key values without overwhelming the LLM.
    """
    if not all_metrics:
        return "No metrics available."

    # Collect all metric names across datasets
    all_keys = set()
    key_samples = {}
    for m in all_metrics:
        for k, v in m.items():
            if not k.startswith("_"):
                all_keys.add(k)
                # Store first non-None sample value
                if k not in key_samples and v is not None:
                    # Truncate long values
                    if isinstance(v, (int, float)):
                        key_samples[k] = round(float(v), 2)
                    elif isinstance(v, str) and len(v) > 80:
                        key_samples[k] = v[:80] + "..."
                    elif isinstance(v, dict):
                        key_samples[k] = f"{{... {len(v)} entries}}"
                    elif isinstance(v, list):
                        key_samples[k] = f"[... {len(v)} items]"
                    else:
                        key_samples[k] = v

    # Categorize metrics
    categories = {
        "Revenue": [],
        "Sales": [],
        "Profit & Margin": [],
        "Expense": [],
        "Inventory": [],
        "Cash Flow": [],
        "Customer": [],
        "Supplier": [],
        "Employee": [],
        "Receivables & Payables": [],
        "Financial Ratios": [],
        "Forecast": [],
        "Other": [],
    }

    for key in sorted(all_keys):
        k_lower = key.lower()
        val_str = f"{key} = {key_samples.get(key, 'N/A')}"
        if "revenue" in k_lower and "growth" not in k_lower:
            categories["Revenue"].append(val_str)
        elif "sale" in k_lower:
            categories["Sales"].append(val_str)
        elif any(w in k_lower for w in ["profit", "margin", "ebitda"]):
            categories["Profit & Margin"].append(val_str)
        elif any(w in k_lower for w in ["expense", "cost_ratio", "spend", "payroll"]):
            categories["Expense"].append(val_str)
        elif "inventory" in k_lower:
            categories["Inventory"].append(val_str)
        elif any(w in k_lower for w in ["cashflow", "cash_", "burn", "runway"]):
            categories["Cash Flow"].append(val_str)
        elif any(w in k_lower for w in ["customer", "client"]):
            categories["Customer"].append(val_str)
        elif any(w in k_lower for w in ["supplier", "vendor"]):
            categories["Supplier"].append(val_str)
        elif any(w in k_lower for w in ["employee", "headcount", "staff"]):
            categories["Employee"].append(val_str)
        elif any(w in k_lower for w in ["receivable", "payable", "collection", "payment_period"]):
            categories["Receivables & Payables"].append(val_str)
        elif any(w in k_lower for w in ["ratio", "debt", "equity", "asset", "liability", "working_capital", "return_on"]):
            categories["Financial Ratios"].append(val_str)
        elif any(w in k_lower for w in ["forecast", "projection"]):
            categories["Forecast"].append(val_str)
        elif "growth" in k_lower or "volatility" in k_lower or "concentration" in k_lower:
            categories["Other"].append(val_str)
        else:
            categories["Other"].append(val_str)

    # Build summary
    lines = []
    total_metrics = 0
    for cat, items in categories.items():
        if items:
            lines.append(f"\n  {cat} ({len(items)} metrics):")
            for item in items[:10]:  # Max 10 per category
                lines.append(f"    - {item}")
            if len(items) > 10:
                lines.append(f"    ... and {len(items) - 10} more")
            total_metrics += len(items)

    lines.append(f"\n  Total unique metrics available: {total_metrics}")
    lines.append(f"  Number of source datasets: {len(all_metrics)}")

    return "\n".join(lines)


def identify_possible_reports(
    all_metrics: List[Dict[str, Any]],
    existing_report_names: List[str],
) -> Dict[str, Any]:
    """
    Use LLM to identify which reports can be generated from the available metrics.

    Args:
        all_metrics: List of metric dicts from all filtered datasets.
        existing_report_names: List of report names already generated.

    Returns:
        Dict with keys: possible_reports, unavailable_reports
    """
    prompt = build_identify_reports_prompt(all_metrics, existing_report_names)
    model = get_model()

    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a senior financial analyst. You return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4000,
    )

    content = response.choices[0].message.content.strip()
    content = _strip_json_fences(content)
    return _parse_json_response(content)


# ──────────────────────────────────────────────────
# Report Generation
# ──────────────────────────────────────────────────

def build_generate_report_prompt(
    report_name: str,
    metrics: Dict[str, Any],
    required_metrics: List[str],
    analysis_summary: str,
) -> str:
    """
    Build the LLM prompt for generating a specific financial report.

    The prompt instructs the LLM to produce a structured report with
    Data, Analysis, and Conclusion sections (and more as appropriate).
    """
    # Filter metrics to only include the required ones (plus context)
    relevant_metrics = {}
    for key in required_metrics:
        if key in metrics:
            relevant_metrics[key] = metrics[key]

    # Also include all non-metadata metrics for context if few were required
    if len(relevant_metrics) < 5:
        for key, val in metrics.items():
            if not key.startswith("_") and key not in relevant_metrics:
                relevant_metrics[key] = val

    metrics_str = json.dumps(relevant_metrics, indent=2, default=str)

    prompt = f"""You are a senior financial analyst writing a professional report. Generate a comprehensive "{report_name}".

DATASET CONTEXT:
{analysis_summary if analysis_summary else "No additional context available."}

AVAILABLE METRICS:
```json
{metrics_str}
```

INSTRUCTIONS:
1. Write a thorough, professional financial report.
2. The report MUST include these core sections:
   - **Data**: Present the relevant metrics and data points clearly. Include specific numbers.
   - **Analysis**: Interpret the data. Identify trends, patterns, strengths, and weaknesses.
   - **Conclusion**: Summarize key findings and provide actionable recommendations.
3. Additional sections may include (as appropriate to the report type):
   - **Executive Summary** (for summary reports)
   - **Methodology** (if explaining how metrics were derived)
   - **Risk Assessment** (for financial health / growth reports)
   - **Recommendations** (if distinct from conclusion)
   - **Comparison** (benchmarking or period-over-period)
4. Each section must have substantive content - no placeholders.
5. Write in a professional tone suitable for stakeholders and executives.
6. Use numeric data from the metrics where available. Do not fabricate data.
7. If a metric is missing or unclear, note that honestly.

Return your response as a JSON object where:
- The top-level key is the EXACT report name
- Each nested key is a section header
- Each nested value is the section content (can be multi-paragraph)

Example format:
{{
    "{report_name}": {{
        "Data": "The company reported total revenue of $X...\\n\\nKey metrics include...",
        "Analysis": "Revenue has shown a X% growth trend...\\n\\nSeveral factors contribute...",
        "Conclusion": "Based on the analysis, the company should..."
    }}
}}

Return ONLY valid JSON, no other text. Do NOT wrap the JSON in markdown code fences.
"""
    return prompt


def generate_report(
    report_name: str,
    metrics: Dict[str, Any],
    required_metrics: List[str],
    analysis_summary: str = "",
) -> Dict[str, Any]:
    """
    Generate a single financial report using the LLM.

    Args:
        report_name: Name of the report to generate (e.g., "Revenue Report").
        metrics: Full metrics dict with all available metrics.
        required_metrics: List of metric keys needed for this report.
        analysis_summary: Summary from subAgent1's analysis for context.

    Returns:
        A dict in the format: {"Report Name": {"Section Header": "content", ...}}
    """
    prompt = build_generate_report_prompt(
        report_name, metrics, required_metrics, analysis_summary
    )
    model = get_model()

    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior financial analyst writing professional reports. "
                    "You return only valid JSON with the report name as the top-level key "
                    "and section headers as nested keys. Each section contains detailed, "
                    "substantive content. You do not wrap the JSON in markdown code fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,  # Slightly higher temperature for narrative generation
        max_tokens=8000,
    )

    content = response.choices[0].message.content.strip()
    content = _strip_json_fences(content)

    result = _parse_json_response(content)

    # Ensure the report name is the top-level key
    if report_name not in result:
        # LLM might have used a slightly different casing
        for key in list(result.keys()):
            if key.lower() == report_name.lower():
                result[report_name] = result.pop(key)
                break
        else:
            # Wrap the result with the report name
            result = {report_name: result}

    return result


# ──────────────────────────────────────────────────
# Heuristic fallback (no LLM)
# ──────────────────────────────────────────────────

def heuristic_identify_reports(
    all_metrics: List[Dict[str, Any]],
    existing_report_names: List[str],
) -> Dict[str, Any]:
    """
    Fallback: Identify possible reports based on metric name patterns.

    Used when the LLM is unavailable.
    """
    if not all_metrics:
        return {"possible_reports": [], "unavailable_reports": []}

    # Collect all metric names
    all_keys = set()
    for m in all_metrics:
        all_keys.update(k for k in m.keys() if not k.startswith("_"))

    # Report-to-required-keywords mapping
    report_keywords = {
        "Executive Financial Summary Report": ["total_revenue", "net_profit", "gross_margin"],
        "Revenue Report": ["revenue"],
        "Sales Report": ["sales", "average_order"],
        "Profit & Loss Report": ["profit", "margin", "expense"],
        "Expense Report": ["expense"],
        "Cash Flow Report": ["cashflow", "cash_"],
        "Inventory Report": ["inventory"],
        "Product Performance Report": ["product", "highest_selling", "lowest_selling"],
        "Supplier Report": ["supplier"],
        "Customer Report": ["customer"],
        "Accounts Receivable Report": ["receivable", "collection"],
        "Accounts Payable Report": ["payable", "payment_period"],
        "Payroll Report": ["payroll", "employee"],
        "Financial Health Report": ["ratio", "debt", "equity", "return_on"],
        "Business Growth Report": ["growth", "forecast"],
    }

    possible = []
    unavailable = []

    for report_name, keywords in report_keywords.items():
        if report_name in existing_report_names:
            continue

        matched = [k for k in all_keys if any(kw in k.lower() for kw in keywords)]
        if matched:
            possible.append({
                "report_name": report_name,
                "required_metrics": matched,
                "confidence": "high" if len(matched) >= 3 else "medium",
                "rationale": f"Found {len(matched)} relevant metrics: {', '.join(matched[:5])}",
            })
        else:
            unavailable.append({
                "report_name": report_name,
                "reason": "No relevant metrics found in available data.",
            })

    return {
        "possible_reports": possible,
        "unavailable_reports": unavailable,
    }


def heuristic_generate_report(
    report_name: str,
    metrics: Dict[str, Any],
    required_metrics: List[str],
    analysis_summary: str = "",
) -> Dict[str, Any]:
    """
    Fallback: Generate a basic report template from metrics without LLM.

    Used when the LLM is unavailable.
    """
    # Filter to relevant metrics
    relevant = {}
    for key in required_metrics:
        if key in metrics:
            relevant[key] = metrics[key]

    # Build data section
    data_lines = ["The following metrics are available for this report:"]
    for key, val in sorted(relevant.items()):
        if val is not None:
            data_lines.append(f"  - {key}: {val}")
    data_section = "\n".join(data_lines)

    analysis_section = (
        "Automated heuristic analysis. "
        "A detailed analysis could not be generated because the LLM was unavailable. "
        f"The dataset contains {len(relevant)} metrics relevant to this report type. "
        "Key metrics include: " + ", ".join(relevant.keys())[:200] + "."
    )

    conclusion_section = (
        "Automated heuristic conclusion. "
        "For a full analysis with actionable recommendations, "
        "please ensure the LLM (OpenRouter) is configured and retry."
    )

    return {
        report_name: {
            "Data": data_section,
            "Analysis": analysis_section,
            "Conclusion": conclusion_section,
            "_heuristic_fallback": "true",
        }
    }
