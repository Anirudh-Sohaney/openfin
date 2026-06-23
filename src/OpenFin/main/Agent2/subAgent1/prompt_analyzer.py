import os
import json
from typing import Dict
from main.llm_client import get_llm_client, get_model





def build_analysis_prompt(user_prompt: str) -> str:
    prompt = f"""You are a financial data analyst. Your job is to analyze the user's question and determine what data is needed to answer it.

AVAILABLE DATA SOURCES:
1. "filtered-data" — JSON files with computed financial metrics like:
   total_revenue, yearly_revenue, yearly_revenue_list, total_sales, yearly_sales, yearly_sales_list
   total_units_sold, highest_revenue_product, lowest_revenue_product, gross_profit,
   gross_margin, return_rate, average_order_value, total_expenses,
   marketing_spend, shipping_costs, sales_growth, revenue_growth,
   highest_selling_product, lowest_selling_product, forecasted_revenue

2. "base-reports" — Professional PDF reports stored in main/reports/base-reports/
   containing structured narratives (Executive Summary, Data, Analysis, Conclusions)
   about: revenue, sales, profit & loss, expenses, financial health,
   product performance, business growth. Text extracted from PDFs.

3. "insights" — Professional PDF reports stored in main/reports/insights/
   containing research-driven analysis and financial issue reports. Text extracted
   from PDFs. Covers: pricing optimization, cost reduction, operational efficiency,
   revenue diversification, market opportunities, risk assessment.

4. "internet" — Live web search via Tavily for external information.

USER PROMPT: "{user_prompt}"

Return a JSON object with this exact structure:
{{
    "data_source": "filtered-data | base-reports | insights | internet",
    "data_keywords": ["keyword1", "keyword2"],
    "required_data_fields": ["field1", "field2"],
    "tavily_query": "search query string or null",
    "summary": "what the user is asking for"
}}

RULES:
- "filtered-data" is for raw metrics/numbers. "base-reports" is for structured
  PDF reports with narrative analysis.
- "insights" is for financial concerns, issues, overall financial health
  (PDF reports with research-backed analysis).
- "internet" is for external info (suppliers, competitors, market trends).
- data_keywords: the financial concepts mentioned (revenue, sales, profit,
  products, expenses, growth, pricing, etc.)
- required_data_fields: SPECIFIC metric/field names needed to answer the prompt.
  If the prompt requires calculation (projection, growth rate, comparison, sum, etc.),
  list the data fields needed as input for that calculation.
  Example: prompt "projected sales" → ["yearly_sales_list", "sales_growth"]
  Example: prompt "annual revenue" → ["total_revenue", "yearly_revenue"]
  Empty list if internet source or if the data comes from PDF text.
- tavily_query: specific search string when source is "internet", else null.
- summary: one sentence explaining what the user wants.

Return ONLY valid JSON, no other text.
"""
    return prompt


def analyze_prompt(user_prompt: str) -> Dict:
    model = get_model()
    prompt = build_analysis_prompt(user_prompt)

    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a financial data analyst. You return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
        else:
            raise ValueError(f"LLM returned invalid JSON: {content[:500]}")

    return result
