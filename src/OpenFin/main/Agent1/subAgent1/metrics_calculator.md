# metrics_calculator.py

## Key Objective
Calculates all derivable financial metrics (~80+) from a standardized DataFrame using column mappings identified by the LLM. Produces a flat dictionary of metric_name → value.

## Tools / Algorithms Used
- **pandas**: Time-series resampling, groupby aggregations, numeric type coercion.
- **numpy**: Growth rate averaging and statistical calculations.
- **HHI (Herfindahl-Hirschman Index)**: Used for concentration scores (customer, supplier, revenue, profit).
- **Simple linear projection**: For forecasted metrics (average period-over-period change extrapolated).
- **Safe division**: All division operations guard against zero/None/NaN values.

## Key Objects

### `MetricsCalculator` (class)
Main calculation engine. Instantiated with DataFrame, date column, column mappings, derivable metrics list, and timeframes.

**Constructor parameters:**
- `df: pd.DataFrame` - Standardized DataFrame (date kept as a column, not the index).
- `date_col: Optional[str]` - Name of the date column.
- `mappings: Dict[str, Any]` - Column mappings from LLM analysis.
- `derivable_metrics: List[str]` - List of metric names to compute.
- `timeframes: Optional[List[str]]` - Available timeframes.

Deduplicates expense columns against individually-mapped columns (cost, marketing, etc.) to prevent double-counting. Caches total expenses via `_cached_total_expenses`.

#### `calculate_all() -> Dict[str, Any]`
- **Use**: Computes all derivable metrics and returns a flat dict. Calls all `_calc_*` methods in sequence.

#### Category calculation methods:
- `_calc_revenue_metrics()` - Total, yearly, quarterly, monthly revenue and growth rates.
- `_calc_sales_metrics()` - Total, periodic sales, AOV, units sold, sales growth.
- `_calc_product_metrics()` - Highest/lowest selling/revenue/profit/margin products, product scores, growth rates, lifetime value.
- `_calc_profit_metrics()` - Gross/net/operating profit, margins, growth, volatility, margin compression.
- `_calc_inventory_metrics()` - Inventory value, turnover, age, expenses, carrying cost, overstocked/understocked, movement speed.
- `_calc_expense_metrics()` - Total/periodic expenses, growth, ratios (expense-to-revenue, payroll, marketing, logistics, discount). Uses `_build_expense_series()` helper to construct monthly total-expense resampled series.
- `_calc_employee_metrics()` - Revenue per employee, profit per employee.
- `_calc_receivables_payables()` - AR, AP, overdue, collection/payment periods.
- `_calc_cashflow_metrics()` - Operating/net/free cashflow, reserves, burn rate, runway.
- `_calc_customer_metrics()` - Count, growth, retention, repeat purchase, average value, concentration, profitability.
- `_calc_supplier_metrics()` - Count, concentration, dependency, largest spend, cost growth, cost impact.
- `_calc_ratio_metrics()` - Debt-to-equity, current/quick ratios, working capital, ROA, ROE, ROI, break-even.
- `_calc_forecast_metrics()` - Simple linear projections for revenue, profit, cashflow, demand.
- `_calc_misc_metrics()` - Return/refund rates, concentration scores, seasonal demand, peak/lowest months.

### `calculate_metrics(df, date_col, mappings, derivable_metrics, timeframes) -> Dict[str, Any]`
- **Parameters**: Same as MetricsCalculator constructor.
- **Use**: Convenience function wrapping `MetricsCalculator.calculate_all()`.
