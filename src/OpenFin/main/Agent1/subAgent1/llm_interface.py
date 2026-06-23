"""
llm_interface.py
Key objective: Interface with an LLM to analyze data variables and determine which
financial metrics can and should be derived from the uploaded data.

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
import pandas as pd
from typing import Optional, Dict, List
from main.llm_client import get_llm_client, get_model


# All known derivable metrics (from specs.md)
ALL_KNOWN_METRICS = [
    "total_revenue", "yearly_revenue", "quarterly_revenue", "monthly_revenue",
    "revenue_growth", "yearly_revenue_growth", "quarterly_revenue_growth",
    "monthly_revenue_growth", "total_sales", "yearly_sales", "quarterly_sales",
    "monthly_sales", "sales_growth", "average_order_value", "total_units_sold",
    "highest_selling_product", "lowest_selling_product", "highest_revenue_product",
    "lowest_revenue_product", "highest_profit_product", "lowest_profit_product",
    "highest_margin_product", "lowest_margin_product", "gross_profit", "net_profit",
    "operating_profit", "gross_margin", "net_margin", "operating_margin",
    "profit_growth", "inventory_value", "inventory_turnover",
    "inventory_turnover_days", "average_inventory_age", "inventory_expenses",
    "monthly_inventory_expenses", "quarterly_inventory_expenses",
    "yearly_inventory_expenses", "inventory_carrying_cost",
    "overstocked_inventory_value", "understocked_inventory_value",
    "slowest_moving_product", "fastest_moving_product", "total_expenses",
    "monthly_expenses", "quarterly_expenses", "yearly_expenses", "expense_growth",
    "expense_to_revenue_ratio", "payroll_expenses", "payroll_to_revenue_ratio",
    "revenue_per_employee", "profit_per_employee", "accounts_receivable",
    "overdue_receivables", "average_collection_period", "accounts_payable",
    "average_payment_period", "operating_cashflow", "net_cashflow", "free_cashflow",
    "cash_reserves", "cash_burn_rate", "cash_runway", "customer_count",
    "customer_growth_rate", "customer_retention_rate", "repeat_purchase_rate",
    "average_customer_value", "largest_customer_revenue_share", "supplier_count",
    "supplier_concentration", "supplier_dependency_score", "largest_supplier_spend",
    "supplier_cost_growth", "seasonal_demand_score", "peak_sales_month",
    "lowest_sales_month", "product_profitability_score", "product_growth_rate",
    "margin_compression_rate", "revenue_concentration_score",
    "profit_concentration_score", "customer_concentration_score", "return_rate",
    "refund_rate", "discount_rate", "marketing_spend", "marketing_roi",
    "shipping_costs", "logistics_cost_ratio", "fixed_costs", "variable_costs",
    "debt_to_equity_ratio", "current_ratio", "quick_ratio", "working_capital",
    "return_on_assets", "return_on_equity", "return_on_investment",
    "break_even_point", "profit_volatility", "revenue_volatility",
    "expense_volatility", "inventory_growth_rate", "forecasted_revenue",
    "forecasted_profit", "forecasted_demand", "forecasted_cashflow",
    "highest_growth_product", "fastest_declining_product",
    "product_lifetime_value", "average_profit_per_sale", "average_profit_per_product",
    "top_customer_profitability", "top_supplier_cost_impact",
]




def _make_json_safe(obj):
    """Convert non-JSON-serializable objects (Timestamp, etc.) to strings."""
    if isinstance(obj, (pd.Timestamp, pd.Period)):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    return obj


def describe_dataframe(df: pd.DataFrame, date_col: Optional[str]) -> Dict:
    """
    Build a structured description of the DataFrame to send to the LLM.
    """
    description = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [],
        "sample_rows": _make_json_safe(df.head(5).to_dict(orient="records")),
        "date_column": date_col,
    }

    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null_count": int(df[col].notna().sum()),
            "null_count": int(df[col].isna().sum()),
            "unique_count": int(df[col].nunique()),
        }

        # Numeric summary
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info["min"] = float(df[col].min()) if pd.notna(df[col].min()) else None
            col_info["max"] = float(df[col].max()) if pd.notna(df[col].max()) else None
            col_info["mean"] = float(df[col].mean()) if pd.notna(df[col].mean()) else None
            col_info["sum"] = float(df[col].sum()) if pd.notna(df[col].sum()) else None

        # Categorical summary
        if not pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique() < 20:
            sample_vals = df[col].dropna().unique()[:10].tolist()
            col_info["sample_values"] = [str(v) for v in sample_vals]

        description["columns"].append(col_info)

    return description


def build_analysis_prompt(data_description: Dict) -> str:
    """Build the prompt for the LLM to analyze the data."""
    known_metrics_str = "\n".join(f"  - {m}" for m in ALL_KNOWN_METRICS)
    prompt = f"""You are a financial data analyst. Analyze the following dataset description and determine which financial metrics can be derived.

DATASET DESCRIPTION:
- Row count: {data_description['row_count']}
- Column count: {data_description['column_count']}
- Date column identified: {data_description['date_column']}

COLUMNS:
{json.dumps(data_description['columns'], indent=2)}

SAMPLE ROWS:
{json.dumps(data_description['sample_rows'], indent=2)}

AVAILABLE METRICS TO CHOOSE FROM:
{known_metrics_str}

INSTRUCTIONS:
1. Examine the columns and identify which columns represent:
   - Date/period columns (for time-series analysis)
   - Revenue/sales revenue columns (MONETARY amount earned, e.g. "revenue", "income")
   - Product/item identifiers
   - Quantity/units sold columns (UNIT COUNT, e.g. "units_sold", "qty" — NOT monetary)
   - Unit price columns (PER-UNIT price, e.g. "unit_price", "price_per_unit" — when total revenue column is absent but qty × unit_price can derive revenue)
   - Unit cost columns (PER-UNIT cost, e.g. "unit_cost" — when total cost column is absent but qty × unit_cost can derive cost)
   - Cost/expense columns
   - Profit columns
   - Customer identifiers
   - Supplier identifiers
   - Inventory-related columns
   - Cash flow columns
   - Receivables/payables columns
   - Discount/return columns
   - Marketing/spend columns
   - Employee count columns
   - Debt/equity/asset columns

CRITICAL DISTINCTION:
- "sales_column" must be a MONETARY column (revenue/sales in dollars).
- "quantity_column" must be a UNIT COUNT column (number of items sold).
- These two MUST NOT be the same column. If there is no separate monetary sales column
  (e.g., only one revenue column exists), set sales_column to null.
- If a column is named "units_sold" or similar, it is quantity_column, NOT sales_column.
- If the dataset has BOTH "quantity_column" and a "unit_price_column" but NO explicit
  "revenue_column", set "unit_price_column" so revenue can be DERIVED as qty × unit_price.
- If the dataset has BOTH "quantity_column" and a "unit_cost_column" but NO explicit
  "cost_column", set "unit_cost_column" so cost can be DERIVED as qty × unit_cost.

2. Return a JSON object with this exact structure:
{{
    "column_mappings": {{
        "date_column": "name_of_date_column_or_null",
        "revenue_column": "name_or_null",
        "sales_column": "name_of_SALES_REVENUE_column_or_null",
        "product_id_column": "name_or_null",
        "product_name_column": "name_or_null",
        "quantity_column": "name_of_UNITS_SOLD_column_or_null",
        "unit_price_column": "name_of_per_unit_price_column_or_null",
        "cost_column": "name_or_null",
        "unit_cost_column": "name_of_per_unit_cost_column_or_null",
        "expense_columns": ["list", "of", "column", "names"],
        "profit_column": "name_or_null",
        "customer_id_column": "name_or_null",
        "customer_name_column": "name_or_null",
        "supplier_id_column": "name_or_null",
        "supplier_name_column": "name_or_null",
        "supplier_cost_column": "name_or_null",
        "inventory_value_column": "name_or_null",
        "inventory_quantity_column": "name_or_null",
        "inventory_cost_column": "name_or_null",
        "receivables_column": "name_or_null",
        "payables_column": "name_or_null",
        "cashflow_column": "name_or_null",
        "cash_reserves_column": "name_or_null",
        "discount_column": "name_or_null",
        "return_column": "name_or_null",
        "refund_column": "name_or_null",
        "marketing_spend_column": "name_or_null",
        "shipping_cost_column": "name_or_null",
        "fixed_cost_column": "name_or_null",
        "variable_cost_column": "name_or_null",
        "employee_count_column": "name_or_null",
        "debt_column": "name_or_null",
        "equity_column": "name_or_null",
        "assets_column": "name_or_null",
        "order_value_column": "name_or_null",
        "additional_notes": "any other observations"
    }},
    "derivable_metrics": ["metric1", "metric2", ...],
    "timeframe_available": ["3_months", "6_months", "12_months", "24_months", "36_months"],
    "analysis_summary": "brief summary of what this dataset contains"
}}

Only include metrics from the AVAILABLE METRICS list. Only include timeframes that are actually possible given the data's date range.

Return ONLY valid JSON, no other text.
"""
    return prompt


def analyze_with_llm(df: pd.DataFrame, date_col: Optional[str]) -> Dict:
    """
    Send DataFrame description to LLM and get back column mappings and derivable metrics.

    Returns:
        Dict with keys: column_mappings, derivable_metrics, timeframe_available, analysis_summary
    """
    data_desc = describe_dataframe(df, date_col)
    prompt = build_analysis_prompt(data_desc)

    model = get_model()

    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a financial data analysis expert. You return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=4000,
    )

    content = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json or ```) and last line (```)
        content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: try to extract JSON from the response
        import re
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
        else:
            raise ValueError(f"LLM returned invalid JSON: {content[:500]}")

    return result


def _validate_mappings(mappings: Dict) -> Dict:
    """
    Post-process column mappings to fix common LLM mistakes.
    - If sales_column equals quantity_column, clear sales_column (fallback to revenue).
    - If sales_column doesn't look like a monetary column, clear it.
    """
    sales_col = mappings.get("sales_column")
    qty_col = mappings.get("quantity_column")

    # If sales and quantity point to the same column, it's a mistake
    if sales_col and qty_col and sales_col == qty_col:
        print(f"  Warning: LLM mapped both sales and quantity to '{sales_col}'. Clearing sales_column.")
        mappings["sales_column"] = None

    # If sales_column name contains unit/qty keywords, it's likely not monetary
    if sales_col:
        sale_lower = sales_col.lower().replace(" ", "_")
        quantity_keywords = ["units", "qty", "quantity", "count", "volume"]
        if any(kw in sale_lower for kw in quantity_keywords):
            print(f"  Warning: sales_column '{sales_col}' looks like a quantity column. Clearing sales_column.")
            mappings["sales_column"] = None

    # Also check if quantity_column was mapped to a revenue/price column
    rev_col = mappings.get("revenue_column")
    if qty_col and rev_col and qty_col == rev_col:
        print(f"  Warning: quantity_column mapped to revenue column '{qty_col}'. Clearing quantity_column.")
        mappings["quantity_column"] = None


def analyze_dataframe(df: pd.DataFrame, date_col: Optional[str]) -> Dict:
    """
    Main entry point: analyze a DataFrame using LLM and return the analysis result.
    Falls back to heuristic analysis if LLM is unavailable.
    """
    try:
        result = analyze_with_llm(df, date_col)
        # Post-process to catch common LLM column mapping mistakes
        if "column_mappings" in result:
            _validate_mappings(result["column_mappings"])
        return result
    except Exception as e:
        print(f"LLM analysis failed ({e}), falling back to heuristic analysis.")
        return heuristic_analysis(df, date_col)


def heuristic_analysis(df: pd.DataFrame, date_col: Optional[str]) -> Dict:
    """
    Heuristic fallback: identify columns by name patterns without LLM.
    """
    columns_lower = {col.lower().replace(" ", "_"): col for col in df.columns}
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    def find_col(patterns):
        for p in patterns:
            if p in columns_lower:
                return columns_lower[p]
        # Try partial matches
        for col_key, col_name in columns_lower.items():
            for p in patterns:
                if p in col_key:
                    return col_name
        return None

    mappings = {
        "date_column": date_col,
        "revenue_column": find_col(["revenue", "total_revenue", "income", "sales_revenue", "turnover"]),
        "sales_column": find_col(["sales", "total_sales", "revenue"]),
        "product_id_column": find_col(["product_id", "sku", "item_id", "product_code"]),
        "product_name_column": find_col(["product", "product_name", "item", "item_name", "description"]),
        "quantity_column": find_col(["quantity", "qty", "units", "volume", "count"]),
        "unit_price_column": find_col(["unit_price", "price_per_unit", "sale_price", "price"]),
        "cost_column": find_col(["cost", "cogs", "cost_of_goods", "total_cost"]),
        "unit_cost_column": find_col(["unit_cost", "cost_per_unit"]),
        "expense_columns": [],
        "profit_column": find_col(["profit", "net_profit", "gross_profit", "operating_profit", "ebitda", "net_income"]),
        "customer_id_column": find_col(["customer_id", "client_id", "account_id"]),
        "customer_name_column": find_col(["customer", "client", "customer_name", "client_name"]),
        "supplier_id_column": find_col(["supplier_id", "vendor_id"]),
        "supplier_name_column": find_col(["supplier", "vendor", "supplier_name"]),
        "supplier_cost_column": find_col(["supplier_cost", "purchase_cost", "procurement_cost"]),
        "inventory_value_column": find_col(["inventory_value", "stock_value", "inventory"]),
        "inventory_quantity_column": find_col(["inventory_qty", "stock_qty", "inventory_quantity"]),
        "inventory_cost_column": find_col(["inventory_cost", "holding_cost"]),
        "receivables_column": find_col(["receivables", "accounts_receivable", "ar"]),
        "payables_column": find_col(["payables", "accounts_payable", "ap"]),
        "cashflow_column": find_col(["cashflow", "cash_flow", "operating_cashflow"]),
        "cash_reserves_column": find_col(["cash", "cash_reserves", "cash_balance"]),
        "discount_column": find_col(["discount", "discounts"]),
        "return_column": find_col(["returns", "return"]),
        "refund_column": find_col(["refund", "refunds"]),
        "marketing_spend_column": find_col(["marketing", "advertising", "ad_spend", "promotion"]),
        "shipping_cost_column": find_col(["shipping", "freight", "logistics", "delivery"]),
        "fixed_cost_column": find_col(["fixed_cost", "fixed_costs", "overhead"]),
        "variable_cost_column": find_col(["variable_cost", "variable_costs"]),
        "employee_count_column": find_col(["employees", "employee_count", "headcount", "staff"]),
        "debt_column": find_col(["debt", "liabilities", "long_term_debt"]),
        "equity_column": find_col(["equity", "shareholder_equity", "owner_equity"]),
        "assets_column": find_col(["assets", "total_assets"]),
        "order_value_column": find_col(["order_value", "aov", "average_order", "basket_size"]),
        "additional_notes": "Heuristic analysis - column names matched by pattern",
    }

    # Identify expense columns (numeric columns that aren't already mapped)
    mapped_cols = set(v for k, v in mappings.items() if isinstance(v, str))
    mappings["expense_columns"] = [
        c for c in numeric_cols
        if c not in mapped_cols
        and any(kw in c.lower().replace(" ", "_") for kw in ["expense", "cost", "spend", "fee", "charge"])
    ]

    # Determine derivable metrics
    derivable = []
    # Always derivable if we have basic numeric data
    always_possible = [
        "total_revenue", "total_sales", "total_expenses",
        "gross_profit", "net_profit", "gross_margin", "net_margin",
        "revenue_growth", "sales_growth", "profit_growth",
    ]
    derivable.extend(always_possible)

    if mappings["product_id_column"]:
        derivable.extend([
            "highest_selling_product", "lowest_selling_product",
            "highest_revenue_product", "lowest_revenue_product",
            "highest_profit_product", "lowest_profit_product",
            "product_profitability_score", "product_growth_rate",
        ])
    if mappings["customer_id_column"]:
        derivable.extend([
            "customer_count", "customer_growth_rate",
            "largest_customer_revenue_share", "customer_concentration_score",
        ])
    if mappings["inventory_value_column"]:
        derivable.extend([
            "inventory_value", "inventory_turnover", "average_inventory_age",
        ])
    if mappings["receivables_column"]:
        derivable.extend(["accounts_receivable", "average_collection_period"])
    if mappings["payables_column"]:
        derivable.extend(["accounts_payable", "average_payment_period"])
    if mappings["employee_count_column"]:
        derivable.extend(["revenue_per_employee", "profit_per_employee"])
    if date_col:
        derivable.extend([
            "yearly_revenue", "quarterly_revenue", "monthly_revenue",
            "yearly_sales", "quarterly_sales", "monthly_sales",
            "seasonal_demand_score", "peak_sales_month", "lowest_sales_month",
        ])

    return {
        "column_mappings": mappings,
        "derivable_metrics": list(set(derivable)),
        "timeframe_available": [],
        "analysis_summary": "Heuristic analysis based on column name pattern matching.",
    }
