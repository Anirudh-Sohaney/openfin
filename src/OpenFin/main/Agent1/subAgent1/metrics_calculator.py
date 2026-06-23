"""
metrics_calculator.py
Key objective: Calculate all derivable financial metrics from the DataFrame
using column mappings identified by the LLM.

Computes ~80+ financial metrics organized by category:
revenue, sales, product, profit, inventory, expenses, employee,
receivables/payables, cash flow, customer, supplier, and ratios.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Any


# ──────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────

def _safe_div(a, b, default=None):
    """Safely divide, returning default on zero/None."""
    try:
        if a is None or b is None or b == 0 or pd.isna(a) or pd.isna(b):
            return default
        return float(a) / float(b)
    except (TypeError, ValueError, ZeroDivisionError):
        return default


def _safe_val(v, default=None):
    """Return float(v) or default if None/NaN."""
    if v is None:
        return default
    try:
        fv = float(v)
        return fv if not pd.isna(fv) else default
    except (TypeError, ValueError):
        return default


def _col_val(df: pd.DataFrame, col: Optional[str], default=None):
    """Get first/sum value from a column if it exists."""
    if col is None or col not in df.columns:
        return default
    try:
        s = pd.to_numeric(df[col], errors="coerce")
        return float(s.sum()) if not pd.isna(s.sum()) else default
    except Exception:
        return default


def _groupby_sum(df: pd.DataFrame, group_col: Optional[str], value_col: Optional[str]) -> pd.Series:
    """Group by group_col and sum value_col."""
    if group_col is None or value_col is None:
        return pd.Series(dtype=float)
    if group_col not in df.columns or value_col not in df.columns:
        return pd.Series(dtype=float)
    return df.groupby(group_col)[value_col].sum().sort_values(ascending=False)


def _groupby_count(df: pd.DataFrame, group_col: Optional[str]) -> pd.Series:
    """Group by group_col and count rows."""
    if group_col is None or group_col not in df.columns:
        return pd.Series(dtype=int)
    return df.groupby(group_col).size().sort_values(ascending=False)


def _resample_series(df: pd.DataFrame, date_col: Optional[str], value_col: Optional[str], freq: str) -> Optional[pd.Series]:
    """Resample a value column by date frequency, return the series."""
    if date_col is None or value_col is None:
        return None
    if date_col not in df.columns or value_col not in df.columns:
        return None
    try:
        ts = df.set_index(date_col)[value_col]
        numeric = pd.to_numeric(ts, errors="coerce")
        return numeric.resample(freq).sum().dropna()
    except Exception:
        return None


def _growth_rate(series: pd.Series) -> Optional[float]:
    """Compute period-over-period growth rate from a sorted series."""
    if series is None or len(series) < 2:
        return None
    vals = series.dropna().values
    if len(vals) < 2:
        return None
    growths = []
    for i in range(1, len(vals)):
        if vals[i - 1] != 0:
            growths.append((vals[i] - vals[i - 1]) / abs(vals[i - 1]))
    return float(np.mean(growths)) if growths else None


# ──────────────────────────────────────────────
# MetricsCalculator
# ──────────────────────────────────────────────

class MetricsCalculator:
    """
    Calculates all derivable financial metrics from a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The standardized DataFrame.
    date_col : str or None
        Name of the date/datetime column.
    mappings : dict
        Column mappings from the LLM analysis (keys like 'revenue_column', etc.).
    derivable_metrics : list[str]
        List of metric names the LLM identified as derivable.
    timeframes : list[str]
        Available timeframes, e.g. ['3_months', '6_months', '12_months'].
    """

    def __init__(
        self,
        df: pd.DataFrame,
        date_col: Optional[str],
        mappings: Dict[str, Any],
        derivable_metrics: List[str],
        timeframes: Optional[List[str]] = None,
    ):
        self.df = df.copy()
        self.date_col = date_col
        self.mappings = mappings or {}
        self.derivable = set(derivable_metrics or [])
        self.timeframes = timeframes or []
        self.results: Dict[str, Any] = {}
        self._cached_total_expenses: Optional[float] = None

        # Ensure date column is datetime (kept as a column, not the index)
        if self.date_col and self.date_col in self.df.columns:
            if not pd.api.types.is_datetime64_any_dtype(self.df[self.date_col]):
                self.df[self.date_col] = pd.to_datetime(
                    self.df[self.date_col], errors="coerce"
                )

        # Shorthand column accessors
        self._rev = self.mappings.get("revenue_column")
        self._sales = self.mappings.get("sales_column")
        self._qty = self.mappings.get("quantity_column")
        self._unit_price = self.mappings.get("unit_price_column")
        self._profit = self.mappings.get("profit_column")
        self._cost = self.mappings.get("cost_column")
        self._unit_cost = self.mappings.get("unit_cost_column")
        self._prod_id = self.mappings.get("product_id_column")
        self._prod_name = self.mappings.get("product_name_column")
        self._cust_id = self.mappings.get("customer_id_column")
        self._cust_name = self.mappings.get("customer_name_column")
        self._supp_id = self.mappings.get("supplier_id_column")
        self._supp_name = self.mappings.get("supplier_name_column")
        self._supp_cost = self.mappings.get("supplier_cost_column")
        self._exp_cols = self.mappings.get("expense_columns", []) or []
        self._inv_val = self.mappings.get("inventory_value_column")
        self._inv_qty = self.mappings.get("inventory_quantity_column")
        self._inv_cost = self.mappings.get("inventory_cost_column")
        self._recv = self.mappings.get("receivables_column")
        self._payb = self.mappings.get("payables_column")
        self._cashflow = self.mappings.get("cashflow_column")
        self._cash_res = self.mappings.get("cash_reserves_column")
        self._discount = self.mappings.get("discount_column")
        self._returns = self.mappings.get("return_column")
        self._refund = self.mappings.get("refund_column")
        self._mktg = self.mappings.get("marketing_spend_column")
        self._ship = self.mappings.get("shipping_cost_column")
        self._fixed = self.mappings.get("fixed_cost_column")
        self._var = self.mappings.get("variable_cost_column")
        self._emp = self.mappings.get("employee_count_column")
        self._debt = self.mappings.get("debt_column")
        self._equity = self.mappings.get("equity_column")
        self._assets = self.mappings.get("assets_column")
        self._order_val = self.mappings.get("order_value_column")

        # ── Derived revenue: when no explicit revenue_column, build one
        # by multiplying qty × unit_price. This unblocks all revenue/profit/product
        # metrics on datasets like sales_transactions.csv that lack a total
        # monetary column but provide units and per-unit pricing.
        if (self._rev is None or self._rev not in self.df.columns) \
                and self._qty and self._unit_price \
                and self._qty in self.df.columns \
                and self._unit_price in self.df.columns:
            try:
                qty = pd.to_numeric(self.df[self._qty], errors="coerce")
                up = pd.to_numeric(self.df[self._unit_price], errors="coerce")
                self.df["_derived_revenue"] = (qty * up).fillna(0)
                self._rev = "_derived_revenue"
            except Exception:
                pass

        # ── Derived cost: same idea, when no explicit cost_column but
        # qty × unit_cost is available.
        if (self._cost is None or self._cost not in self.df.columns) \
                and self._qty and self._unit_cost \
                and self._qty in self.df.columns \
                and self._unit_cost in self.df.columns:
            try:
                qty = pd.to_numeric(self.df[self._qty], errors="coerce")
                uc = pd.to_numeric(self.df[self._unit_cost], errors="coerce")
                self.df["_derived_cost"] = (qty * uc).fillna(0)
                self._cost = "_derived_cost"
            except Exception:
                pass

        # ── Detect "expense-only" dataset: no revenue, no derived revenue,
        # no quantity (so no product transactions), but expense_columns exist
        # and/or a cost_column is present. On such datasets, cost_column
        # functions as an expense aggregator (not COGS), so we keep it in
        # the expense sum instead of stripping it.
        self._is_expense_dataset = (
            (self._rev is None or self._rev not in self.df.columns)
            and (self._qty is None)
            and (bool(self._exp_cols) or bool(self._cost))
        )

        # Deduplicate expense columns: remove any that are already mapped
        # to specific role columns (marketing, shipping, etc.) to avoid
        # double-counting. On expense-only datasets, cost_column is NOT
        # cost-of-goods — it's the total expense — so it must stay in
        # the expense sum rather than be conflated with COGS.
        non_cost_mapped = {
            self._mktg, self._ship, self._fixed, self._var,
            self._discount, self._returns, self._refund, self._supp_cost,
        }
        if self._is_expense_dataset:
            # Keep cost_column in the expense pool — it IS the expense.
            already_mapped = {c for c in non_cost_mapped if c is not None}
        else:
            already_mapped = {self._cost, *non_cost_mapped} - {None}
        self._exp_cols = [c for c in self._exp_cols if c not in already_mapped]

        # Column used as the main "value" column for product-level aggregations.
        # If we derived revenue above, _val_col picks it up automatically.
        self._val_col = self._rev or self._sales or self._profit

    # ── Public API ────────────────────────────

    def calculate_all(self) -> Dict[str, Any]:
        """Compute all derivable metrics and return a flat dict."""
        self.results = {}

        self._calc_revenue_metrics()
        self._calc_sales_metrics()
        self._calc_product_metrics()
        self._calc_profit_metrics()
        self._calc_inventory_metrics()
        self._calc_expense_metrics()
        self._calc_employee_metrics()
        self._calc_receivables_payables()
        self._calc_cashflow_metrics()
        self._calc_customer_metrics()
        self._calc_supplier_metrics()
        self._calc_ratio_metrics()
        self._calc_forecast_metrics()
        self._calc_misc_metrics()

        # Remove None values
        return {k: v for k, v in self.results.items() if v is not None}

    # ── Revenue Metrics ──────────────────────

    def _calc_revenue_metrics(self):
        rev_col = self._rev
        df = self.df

        # total_revenue
        if "total_revenue" in self.derivable:
            self.results["total_revenue"] = _col_val(df.reset_index(), rev_col)

        # Period revenue totals
        if self.date_col:
            for freq, label in [("ME", "monthly"), ("QE", "quarterly"), ("YE", "yearly")]:
                key = f"{label}_revenue"
                if key in self.derivable:
                    s = _resample_series(df, self.date_col, rev_col, freq)
                    if s is not None and len(s) > 0:
                        self.results[key] = float(s.mean())
                        self.results[f"{label}_revenue_list"] = [float(x) for x in s.values]

            # revenue_growth
            if "revenue_growth" in self.derivable:
                s = _resample_series(df, self.date_col, rev_col, "ME")
                self.results["revenue_growth"] = _growth_rate(s)

            for freq, label in [("ME", "monthly"), ("QE", "quarterly"), ("YE", "yearly")]:
                key = f"{label}_revenue_growth"
                if key in self.derivable:
                    s = _resample_series(df, self.date_col, rev_col, freq)
                    self.results[key] = _growth_rate(s)

    # ── Sales Metrics ────────────────────────

    def _calc_sales_metrics(self):
        sales_col = self._sales or self._rev
        qty_col = self._qty
        df_rst = self.df.reset_index()

        if "total_sales" in self.derivable:
            self.results["total_sales"] = _col_val(df_rst, sales_col)

        if self.date_col:
            for freq, label in [("ME", "monthly"), ("QE", "quarterly"), ("YE", "yearly")]:
                key = f"{label}_sales"
                if key in self.derivable:
                    s = _resample_series(self.df, self.date_col, sales_col, freq)
                    if s is not None and len(s) > 0:
                        self.results[key] = float(s.mean())
                        self.results[f"{label}_sales_list"] = [float(x) for x in s.values]

        if "sales_growth" in self.derivable and self.date_col:
            s = _resample_series(self.df, self.date_col, sales_col, "ME")
            self.results["sales_growth"] = _growth_rate(s)

        if "average_order_value" in self.derivable and sales_col is not None:
            total_sales = _col_val(df_rst, sales_col)
            row_count = len(df_rst)
            self.results["average_order_value"] = _safe_div(total_sales, row_count)

        if "total_units_sold" in self.derivable:
            self.results["total_units_sold"] = _col_val(df_rst, qty_col)

    # ── Product Metrics ──────────────────────

    def _calc_product_metrics(self):
        prod_col = self._prod_name or self._prod_id
        if prod_col is None or self._val_col is None:
            return

        df_rst = self.df.reset_index()
        by_prod = _groupby_sum(df_rst, prod_col, self._val_col)
        by_qty = _groupby_sum(df_rst, prod_col, self._qty) if self._qty else None
        by_profit = _groupby_sum(df_rst, prod_col, self._profit) if self._profit else None
        by_cost = _groupby_sum(df_rst, prod_col, self._cost) if self._cost else None

        if len(by_prod) == 0:
            return

        # Highest / lowest by revenue
        if "highest_revenue_product" in self.derivable:
            self.results["highest_revenue_product"] = by_prod.index[0]
            self.results["highest_revenue_product_value"] = float(by_prod.iloc[0])
        if "lowest_revenue_product" in self.derivable:
            self.results["lowest_revenue_product"] = by_prod.index[-1]
            self.results["lowest_revenue_product_value"] = float(by_prod.iloc[-1])

        # Highest / lowest by quantity
        if by_qty is not None and len(by_qty) > 0:
            if "highest_selling_product" in self.derivable:
                self.results["highest_selling_product"] = by_qty.index[0]
                self.results["highest_selling_product_units"] = float(by_qty.iloc[0])
            if "lowest_selling_product" in self.derivable:
                self.results["lowest_selling_product"] = by_qty.index[-1]
                self.results["lowest_selling_product_units"] = float(by_qty.iloc[-1])

        # Highest / lowest by profit
        if by_profit is not None and len(by_profit) > 0:
            if "highest_profit_product" in self.derivable:
                self.results["highest_profit_product"] = by_profit.index[0]
                self.results["highest_profit_product_value"] = float(by_profit.iloc[0])
            if "lowest_profit_product" in self.derivable:
                self.results["lowest_profit_product"] = by_profit.index[-1]
                self.results["lowest_profit_product_value"] = float(by_profit.iloc[-1])

        # Margin per product (profit / revenue)
        if by_profit is not None and len(by_prod) > 0:
            margins = {}
            for idx in by_prod.index:
                rev = by_prod.get(idx, 0)
                prof = by_profit.get(idx, 0)
                m = _safe_div(prof, rev)
                if m is not None:
                    margins[idx] = m
            if margins:
                sorted_margins = sorted(margins.items(), key=lambda x: x[1], reverse=True)
                if "highest_margin_product" in self.derivable:
                    self.results["highest_margin_product"] = sorted_margins[0][0]
                    self.results["highest_margin_product_value"] = sorted_margins[0][1]
                if "lowest_margin_product" in self.derivable:
                    self.results["lowest_margin_product"] = sorted_margins[-1][0]
                    self.results["lowest_margin_product_value"] = sorted_margins[-1][1]

        # Product profitability score (normalized 0-1)
        if "product_profitability_score" in self.derivable and by_profit is not None:
            scores = {}
            for idx in by_prod.index:
                rev = by_prod.get(idx, 0)
                prof = by_profit.get(idx, 0)
                scores[idx] = _safe_div(prof, rev, 0) or 0
            self.results["product_profitability_score"] = scores

        # Product growth rate (period-over-period for each product)
        if "product_growth_rate" in self.derivable and self.date_col:
            growths = {}
            for prod in by_prod.index[:10]:  # top 10
                prod_mask = df_rst[prod_col] == prod
                prod_df = df_rst[prod_mask].set_index(self.date_col).sort_index()
                # Resample directly on the DateTimeIndex (date is now the index)
                if self._val_col and self._val_col in prod_df.columns:
                    try:
                        numeric = pd.to_numeric(prod_df[self._val_col], errors="coerce")
                        s = numeric.resample("ME").sum().dropna()
                    except Exception:
                        s = None
                else:
                    s = None
                g = _growth_rate(s)
                if g is not None:
                    growths[prod] = g
            if growths:
                self.results["product_growth_rate"] = growths
                if "highest_growth_product" in self.derivable:
                    best = max(growths, key=growths.get)
                    self.results["highest_growth_product"] = best
                    self.results["highest_growth_product_rate"] = growths[best]
                if "fastest_declining_product" in self.derivable:
                    worst = min(growths, key=growths.get)
                    self.results["fastest_declining_product"] = worst
                    self.results["fastest_declining_product_rate"] = growths[worst]

        # Product lifetime value (total revenue for each product)
        if "product_lifetime_value" in self.derivable:
            self.results["product_lifetime_value"] = {idx: float(v) for idx, v in by_prod.items()}

        # Average profit per product
        if "average_profit_per_product" in self.derivable and by_profit is not None:
            self.results["average_profit_per_product"] = float(by_profit.mean()) if len(by_profit) > 0 else None

    # ── Profit Metrics ───────────────────────

    def _calc_profit_metrics(self):
        df_rst = self.df.reset_index()
        rev = _col_val(df_rst, self._rev)
        cost = _col_val(df_rst, self._cost)
        profit_col = self._profit

        total_exp = self._calc_total_expenses()

        # gross_profit: revenue - cost
        if "gross_profit" in self.derivable and rev is not None:
            gross = rev - (cost or 0) if cost is not None else rev
            self.results["gross_profit"] = gross

        # net_profit: prefer explicit column, else gross - expenses
        if "net_profit" in self.derivable:
            if profit_col is not None:
                self.results["net_profit"] = _col_val(df_rst, profit_col)
            elif rev is not None and total_exp is not None:
                gross = rev - (cost or 0) if cost is not None else rev
                self.results["net_profit"] = gross - total_exp

        # operating_profit: gross - operating expenses (expense cols)
        if "operating_profit" in self.derivable:
            gross = self.results.get("gross_profit", rev)
            if gross is not None and total_exp is not None:
                self.results["operating_profit"] = gross - total_exp

        # Margins
        for label, key in [("gross_margin", "gross_profit"), ("net_margin", "net_profit"), ("operating_margin", "operating_profit")]:
            if label in self.derivable:
                p = self.results.get(key)
                self.results[label] = _safe_div(p, rev)

        # profit_growth
        if "profit_growth" in self.derivable and self.date_col:
            s = _resample_series(self.df, self.date_col, profit_col or self._val_col, "ME")
            self.results["profit_growth"] = _growth_rate(s)

        # margin_compression_rate (decline in margin over time)
        if "margin_compression_rate" in self.derivable and self.date_col:
            if rev is not None and rev != 0:
                monthly_rev = _resample_series(self.df, self.date_col, self._rev, "ME")
                monthly_prf = _resample_series(self.df, self.date_col, profit_col, "ME")
                if monthly_rev is not None and monthly_prf is not None:
                    margins = (monthly_prf / monthly_rev).dropna()
                    if len(margins) >= 2:
                        change = (margins.iloc[-1] - margins.iloc[0]) / abs(margins.iloc[0])
                        self.results["margin_compression_rate"] = float(change)

        # profit_volatility (std of monthly profit / mean)
        if "profit_volatility" in self.derivable and self.date_col:
            s = _resample_series(self.df, self.date_col, profit_col or self._val_col, "ME")
            if s is not None and len(s) > 1 and s.mean() != 0:
                self.results["profit_volatility"] = float(s.std() / abs(s.mean()))

        # Average profit per sale
        if "average_profit_per_sale" in self.derivable:
            p = self.results.get("net_profit", _col_val(df_rst, profit_col))
            self.results["average_profit_per_sale"] = _safe_div(p, len(df_rst))

    # ── Inventory Metrics ────────────────────

    def _calc_inventory_metrics(self):
        df_rst = self.df.reset_index()
        inv_val_col = self._inv_val
        inv_qty_col = self._inv_qty
        inv_cost_col = self._inv_cost

        # inventory_value
        if "inventory_value" in self.derivable:
            self.results["inventory_value"] = _col_val(df_rst, inv_val_col)

        # inventory_turnover: COGS / avg inventory
        if "inventory_turnover" in self.derivable:
            cogs = _col_val(df_rst, self._cost) or _col_val(df_rst, inv_cost_col)
            inv_val = self.results.get("inventory_value", _col_val(df_rst, inv_val_col))
            self.results["inventory_turnover"] = _safe_div(cogs, inv_val)

        # inventory_turnover_days: 365 / turnover
        if "inventory_turnover_days" in self.derivable:
            turnover = self.results.get("inventory_turnover")
            self.results["inventory_turnover_days"] = _safe_div(365, turnover)

        # average_inventory_age (rough: 365 / turnover)
        if "average_inventory_age" in self.derivable:
            turnover = self.results.get("inventory_turnover")
            self.results["average_inventory_age"] = _safe_div(365, turnover)

        # inventory expenses
        if "inventory_expenses" in self.derivable:
            self.results["inventory_expenses"] = _col_val(df_rst, inv_cost_col)

        if self.date_col:
            for freq, label in [("ME", "monthly"), ("QE", "quarterly"), ("YE", "yearly")]:
                key = f"{label}_inventory_expenses"
                if key in self.derivable:
                    s = _resample_series(self.df, self.date_col, inv_cost_col, freq)
                    if s is not None and len(s) > 0:
                        self.results[key] = float(s.mean())

        # inventory_carrying_cost (estimated as 20-30% of inventory value)
        if "inventory_carrying_cost" in self.derivable:
            inv_val = self.results.get("inventory_value", _col_val(df_rst, inv_val_col))
            if inv_val is not None:
                self.results["inventory_carrying_cost"] = inv_val * 0.25  # 25% estimate

        # Overstocked / understocked (placeholders based on qty thresholds)
        if inv_qty_col is not None and inv_qty_col in df_rst.columns:
            try:
                qty = pd.to_numeric(df_rst[inv_qty_col], errors="coerce").dropna()
                if len(qty) > 0:
                    mean_qty = qty.mean()
                    std_qty = qty.std()
                    if "overstocked_inventory_value" in self.derivable:
                        overstocked = qty[qty > mean_qty + 2 * std_qty]
                        self.results["overstocked_inventory_value"] = float(overstocked.sum()) if len(overstocked) > 0 else 0
                    if "understocked_inventory_value" in self.derivable:
                        understocked = qty[qty < mean_qty - 2 * std_qty]
                        self.results["understocked_inventory_value"] = float(understocked.sum()) if len(understocked) > 0 else 0
            except Exception:
                pass

        # Fastest / slowest moving products (by quantity)
        if self._prod_name and inv_qty_col:
            by_qty = _groupby_sum(df_rst, self._prod_name, inv_qty_col)
            if by_qty is not None and len(by_qty) > 0:
                if "fastest_moving_product" in self.derivable:
                    self.results["fastest_moving_product"] = by_qty.index[0]
                if "slowest_moving_product" in self.derivable:
                    self.results["slowest_moving_product"] = by_qty.index[-1]

        # inventory_growth_rate
        if "inventory_growth_rate" in self.derivable and self.date_col:
            s = _resample_series(self.df, self.date_col, inv_val_col or inv_qty_col, "ME")
            self.results["inventory_growth_rate"] = _growth_rate(s)

    # ── Expense Metrics ──────────────────────

    def _calc_total_expenses(self) -> Optional[float]:
        """Sum of all expense columns. Cached across calls."""
        if self._cached_total_expenses is not None:
            return self._cached_total_expenses
        df_rst = self.df
        total = 0.0
        found = False
        if self._exp_cols:
            for col in self._exp_cols:
                val = _col_val(df_rst, col)
                if val is not None:
                    total += val
                    found = True
        for col in [self._ship, self._mktg, self._fixed, self._var]:
            val = _col_val(df_rst, col)
            if val is not None:
                total += val
                found = True
        result = total if found else None
        self._cached_total_expenses = result
        return result

    def _build_expense_series(self, df: pd.DataFrame) -> Optional[pd.Series]:
        """Build a monthly-resampled total-expense series."""
        if not self.date_col or self.date_col not in df.columns:
            return None
        all_exp_cols = (self._exp_cols or []) + [c for c in [self._ship, self._mktg, self._fixed, self._var] if c]
        if not all_exp_cols:
            return None
        try:
            temp = df.copy()
            temp["_exp_total"] = temp[all_exp_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
            ts = temp.set_index(self.date_col)["_exp_total"]
            return ts.resample("ME").sum().dropna()
        except Exception:
            return None

    def _calc_expense_metrics(self):
        df_rst = self.df.reset_index()
        total_exp = self._calc_total_expenses()
        rev = _col_val(df_rst, self._rev)

        if "total_expenses" in self.derivable:
            self.results["total_expenses"] = total_exp

        if self.date_col and total_exp is not None:
            for freq, label in [("ME", "monthly"), ("QE", "quarterly"), ("YE", "yearly")]:
                key = f"{label}_expenses"
                if key in self.derivable:
                    all_exp_cols = (self._exp_cols or []) + [c for c in [self._ship, self._mktg, self._fixed, self._var] if c]
                    if all_exp_cols:
                        df_rst["_exp_total"] = df_rst[all_exp_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
                        ts = df_rst.set_index(self.date_col)["_exp_total"]
                        s = ts.resample(freq).sum().dropna()
                        if len(s) > 0:
                            self.results[key] = float(s.mean())

        if "expense_growth" in self.derivable and self.date_col:
            s = self._build_expense_series(df_rst)
            if s is not None:
                self.results["expense_growth"] = _growth_rate(s)

        if "expense_to_revenue_ratio" in self.derivable:
            self.results["expense_to_revenue_ratio"] = _safe_div(total_exp, rev)

        if "payroll_expenses" in self.derivable:
            for col in (self._exp_cols or []):
                col_lower = col.lower()
                if any(kw in col_lower for kw in ["payroll", "salary", "wage", "compensation"]):
                    self.results["payroll_expenses"] = _col_val(df_rst, col)
                    break

        if "payroll_to_revenue_ratio" in self.derivable:
            payroll = self.results.get("payroll_expenses")
            self.results["payroll_to_revenue_ratio"] = _safe_div(payroll, rev)

        if "marketing_spend" in self.derivable:
            self.results["marketing_spend"] = _col_val(df_rst, self._mktg)

        if "marketing_roi" in self.derivable:
            mktg = _col_val(df_rst, self._mktg)
            self.results["marketing_roi"] = _safe_div(rev, mktg) if rev and mktg else None

        if "shipping_costs" in self.derivable:
            self.results["shipping_costs"] = _col_val(df_rst, self._ship)

        if "logistics_cost_ratio" in self.derivable:
            ship = _col_val(df_rst, self._ship)
            self.results["logistics_cost_ratio"] = _safe_div(ship, rev)

        if "fixed_costs" in self.derivable:
            self.results["fixed_costs"] = _col_val(df_rst, self._fixed)

        if "variable_costs" in self.derivable:
            self.results["variable_costs"] = _col_val(df_rst, self._var)

        if "discount_rate" in self.derivable:
            disc = _col_val(df_rst, self._discount)
            self.results["discount_rate"] = _safe_div(disc, rev)

        # revenue_volatility
        if "revenue_volatility" in self.derivable and self.date_col:
            s = _resample_series(self.df, self.date_col, self._rev, "ME")
            if s is not None and len(s) > 1 and s.mean() != 0:
                self.results["revenue_volatility"] = float(s.std() / abs(s.mean()))

        # expense_volatility (using computed total expense series)
        if "expense_volatility" in self.derivable and self.date_col:
            s = self._build_expense_series(df_rst)
            if s is not None and len(s) > 1 and s.mean() != 0:
                self.results["expense_volatility"] = float(s.std() / abs(s.mean()))

    # ── Employee Metrics ─────────────────────

    def _calc_employee_metrics(self):
        df_rst = self.df.reset_index()
        emp_col = self._emp
        rev = _col_val(df_rst, self._rev)
        profit = self.results.get("net_profit", _col_val(df_rst, self._profit))
        emp_count = _col_val(df_rst, emp_col)

        if "revenue_per_employee" in self.derivable:
            self.results["revenue_per_employee"] = _safe_div(rev, emp_count)

        if "profit_per_employee" in self.derivable:
            self.results["profit_per_employee"] = _safe_div(profit, emp_count)

    # ── Receivables & Payables ───────────────

    def _calc_receivables_payables(self):
        df_rst = self.df.reset_index()

        if "accounts_receivable" in self.derivable:
            self.results["accounts_receivable"] = _col_val(df_rst, self._recv)

        if "accounts_payable" in self.derivable:
            self.results["accounts_payable"] = _col_val(df_rst, self._payb)

        # overdue_receivables: if a "due_date" or "overdue" column exists, sum those
        if "overdue_receivables" in self.derivable:
            for col in df_rst.columns:
                if "overdue" in col.lower():
                    self.results["overdue_receivables"] = _col_val(df_rst, col)
                    break

        # average_collection_period: AR / (revenue/365)
        if "average_collection_period" in self.derivable:
            ar = self.results.get("accounts_receivable", _col_val(df_rst, self._recv))
            rev = _col_val(df_rst, self._rev)
            daily_rev = _safe_div(rev, 365)
            self.results["average_collection_period"] = _safe_div(ar, daily_rev)

        # average_payment_period: AP / (COGS/365)
        if "average_payment_period" in self.derivable:
            ap = self.results.get("accounts_payable", _col_val(df_rst, self._payb))
            cogs = _col_val(df_rst, self._cost) or 0
            daily_cogs = _safe_div(cogs, 365)
            self.results["average_payment_period"] = _safe_div(ap, daily_cogs)

    # ── Cash Flow Metrics ────────────────────

    def _calc_cashflow_metrics(self):
        df_rst = self.df.reset_index()

        if "operating_cashflow" in self.derivable:
            self.results["operating_cashflow"] = _col_val(df_rst, self._cashflow)

        if "net_cashflow" in self.derivable:
            self.results["net_cashflow"] = _col_val(df_rst, self._cashflow)

        if "free_cashflow" in self.derivable:
            ocf = _col_val(df_rst, self._cashflow)
            capex = _col_val(df_rst, self._fixed) or 0
            if ocf is not None:
                self.results["free_cashflow"] = ocf - capex

        if "cash_reserves" in self.derivable:
            self.results["cash_reserves"] = _col_val(df_rst, self._cash_res)

        if "cash_burn_rate" in self.derivable and self.date_col:
            s = _resample_series(self.df, self.date_col, self._cashflow, "ME")
            if s is not None and len(s) > 0:
                negative_flows = s[s < 0]
                self.results["cash_burn_rate"] = float(negative_flows.mean()) if len(negative_flows) > 0 else 0

        if "cash_runway" in self.derivable:
            reserves = self.results.get("cash_reserves", _col_val(df_rst, self._cash_res))
            burn = self.results.get("cash_burn_rate")
            if reserves is not None and burn is not None and burn < 0:
                self.results["cash_runway"] = _safe_div(reserves, abs(burn))

    # ── Customer Metrics ─────────────────────

    def _calc_customer_metrics(self):
        df_rst = self.df.reset_index()
        cust_col = self._cust_name or self._cust_id
        if cust_col is None:
            return

        # customer_count
        if "customer_count" in self.derivable:
            self.results["customer_count"] = int(df_rst[cust_col].nunique()) if cust_col in df_rst.columns else None

        # customer_growth_rate (new customers per period)
        if "customer_growth_rate" in self.derivable and self.date_col:
            if cust_col in df_rst.columns and self.date_col in df_rst.columns:
                new_per_month = df_rst.groupby(pd.Grouper(key=self.date_col, freq="ME"))[cust_col].nunique()
                self.results["customer_growth_rate"] = _growth_rate(new_per_month)

        # customer_retention_rate (repeat customers / total)
        if "customer_retention_rate" in self.derivable and cust_col in df_rst.columns:
            cust_counts = df_rst[cust_col].value_counts()
            repeat = (cust_counts > 1).sum()
            total = len(cust_counts)
            self.results["customer_retention_rate"] = _safe_div(repeat, total)

        # repeat_purchase_rate
        if "repeat_purchase_rate" in self.derivable and cust_col in df_rst.columns:
            cust_counts = df_rst[cust_col].value_counts()
            repeat = (cust_counts > 1).sum()
            total = len(cust_counts)
            self.results["repeat_purchase_rate"] = _safe_div(repeat, total)

        # average_customer_value: total revenue / unique customers
        if "average_customer_value" in self.derivable:
            rev = _col_val(df_rst, self._rev)
            cust_count = self.results.get("customer_count", df_rst[cust_col].nunique() if cust_col in df_rst.columns else None)
            self.results["average_customer_value"] = _safe_div(rev, cust_count)

        # largest_customer_revenue_share
        if "largest_customer_revenue_share" in self.derivable:
            cust_rev = _groupby_sum(df_rst, cust_col, self._rev)
            if cust_rev is not None and len(cust_rev) > 0:
                rev = cust_rev.sum()
                self.results["largest_customer_revenue_share"] = _safe_div(cust_rev.iloc[0], rev)

        # customer_concentration_score (HHI-like)
        if "customer_concentration_score" in self.derivable:
            cust_rev = _groupby_sum(df_rst, cust_col, self._rev)
            if cust_rev is not None and len(cust_rev) > 0:
                total = cust_rev.sum()
                if total > 0:
                    shares = cust_rev / total
                    self.results["customer_concentration_score"] = float((shares ** 2).sum())

        # top_customer_profitability
        if "top_customer_profitability" in self.derivable:
            profit_col = self._profit or self._val_col
            cust_prof = _groupby_sum(df_rst, cust_col, profit_col)
            if cust_prof is not None and len(cust_prof) > 0:
                self.results["top_customer_profitability"] = {cust_prof.index[0]: float(cust_prof.iloc[0])}

    # ── Supplier Metrics ─────────────────────

    def _calc_supplier_metrics(self):
        df_rst = self.df.reset_index()
        supp_col = self._supp_name or self._supp_id
        if supp_col is None:
            return

        if "supplier_count" in self.derivable:
            self.results["supplier_count"] = int(df_rst[supp_col].nunique()) if supp_col in df_rst.columns else None

        # supplier_concentration (HHI)
        if "supplier_concentration" in self.derivable:
            supp_spend = _groupby_sum(df_rst, supp_col, self._supp_cost or self._cost)
            if supp_spend is not None and len(supp_spend) > 0 and supp_spend.sum() > 0:
                shares = supp_spend / supp_spend.sum()
                self.results["supplier_concentration"] = float((shares ** 2).sum())

        # supplier_dependency_score (max share)
        if "supplier_dependency_score" in self.derivable:
            supp_spend = _groupby_sum(df_rst, supp_col, self._supp_cost or self._cost)
            if supp_spend is not None and len(supp_spend) > 0 and supp_spend.sum() > 0:
                self.results["supplier_dependency_score"] = float(supp_spend.iloc[0] / supp_spend.sum())

        # largest_supplier_spend
        if "largest_supplier_spend" in self.derivable:
            supp_spend = _groupby_sum(df_rst, supp_col, self._supp_cost or self._cost)
            if supp_spend is not None and len(supp_spend) > 0:
                self.results["largest_supplier_spend"] = float(supp_spend.iloc[0])
                self.results["largest_supplier_name"] = supp_spend.index[0]

        # supplier_cost_growth
        if "supplier_cost_growth" in self.derivable and self.date_col:
            s = _resample_series(self.df, self.date_col, self._supp_cost or self._cost, "ME")
            self.results["supplier_cost_growth"] = _growth_rate(s)

        # top_supplier_cost_impact
        if "top_supplier_cost_impact" in self.derivable:
            supp_spend = _groupby_sum(df_rst, supp_col, self._supp_cost or self._cost)
            if supp_spend is not None and len(supp_spend) > 0:
                total = supp_spend.sum()
                self.results["top_supplier_cost_impact"] = {supp_spend.index[0]: _safe_div(float(supp_spend.iloc[0]), total)}

    # ── Ratio Metrics ────────────────────────

    def _calc_ratio_metrics(self):
        df_rst = self.df.reset_index()

        # debt_to_equity_ratio
        if "debt_to_equity_ratio" in self.derivable:
            debt = _col_val(df_rst, self._debt)
            equity = _col_val(df_rst, self._equity)
            self.results["debt_to_equity_ratio"] = _safe_div(debt, equity)

        # current_ratio: current assets / current liabilities
        if "current_ratio" in self.derivable:
            assets = _col_val(df_rst, self._assets)
            debt = _col_val(df_rst, self._debt)
            self.results["current_ratio"] = _safe_div(assets, debt)

        # quick_ratio: (current assets - inventory) / current liabilities
        if "quick_ratio" in self.derivable:
            assets = _col_val(df_rst, self._assets)
            inv_val = self.results.get("inventory_value", _col_val(df_rst, self._inv_val))
            debt = _col_val(df_rst, self._debt)
            if assets is not None and inv_val is not None:
                self.results["quick_ratio"] = _safe_div(assets - inv_val, debt)

        # working_capital: current assets - current liabilities
        if "working_capital" in self.derivable:
            assets = _col_val(df_rst, self._assets)
            debt = _col_val(df_rst, self._debt)
            if assets is not None and debt is not None:
                self.results["working_capital"] = assets - debt

        # return_on_assets
        if "return_on_assets" in self.derivable:
            profit = self.results.get("net_profit", _col_val(df_rst, self._profit))
            assets = _col_val(df_rst, self._assets)
            self.results["return_on_assets"] = _safe_div(profit, assets)

        # return_on_equity
        if "return_on_equity" in self.derivable:
            profit = self.results.get("net_profit", _col_val(df_rst, self._profit))
            equity = _col_val(df_rst, self._equity)
            self.results["return_on_equity"] = _safe_div(profit, equity)

        # return_on_investment
        if "return_on_investment" in self.derivable:
            profit = self.results.get("net_profit", _col_val(df_rst, self._profit))
            total_cost = _col_val(df_rst, self._cost) or 0
            total_exp = self._calc_total_expenses() or 0
            investment = total_cost + total_exp
            self.results["return_on_investment"] = _safe_div(profit, investment)

        # break_even_point: fixed costs / (1 - variable_cost/revenue)
        if "break_even_point" in self.derivable:
            fixed = _col_val(df_rst, self._fixed) or 0
            rev = _col_val(df_rst, self._rev)
            var = _col_val(df_rst, self._var)
            if rev and rev != 0 and var is not None:
                cm_ratio = 1 - (var / rev)
                self.results["break_even_point"] = _safe_div(fixed, cm_ratio)

    # ── Forecast Metrics ─────────────────────

    def _calc_forecast_metrics(self):
        if not self.date_col:
            return

        # Simple linear projection based on monthly trend
        def _simple_forecast(series: pd.Series, periods: int = 3) -> Optional[float]:
            if series is None or len(series) < 2:
                return None
            vals = series.dropna().values
            if len(vals) < 2:
                return None
            # Average period-over-period change
            changes = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
            avg_change = np.mean(changes)
            return float(vals[-1] + avg_change * periods)

        # forecasted_revenue
        if "forecasted_revenue" in self.derivable:
            s = _resample_series(self.df, self.date_col, self._rev, "ME")
            self.results["forecasted_revenue"] = _simple_forecast(s, 3)

        # forecasted_profit
        if "forecasted_profit" in self.derivable:
            s = _resample_series(self.df, self.date_col, self._profit, "ME")
            self.results["forecasted_profit"] = _simple_forecast(s, 3)

        # forecasted_cashflow
        if "forecasted_cashflow" in self.derivable:
            s = _resample_series(self.df, self.date_col, self._cashflow, "ME")
            self.results["forecasted_cashflow"] = _simple_forecast(s, 3)

        # forecasted_demand (based on quantity)
        if "forecasted_demand" in self.derivable:
            s = _resample_series(self.df, self.date_col, self._qty, "ME")
            self.results["forecasted_demand"] = _simple_forecast(s, 3)

    # ── Miscellaneous Metrics ────────────────

    def _calc_misc_metrics(self):
        df_rst = self.df.reset_index()

        # return_rate
        if "return_rate" in self.derivable:
            returns_val = _col_val(df_rst, self._returns)
            rev = _col_val(df_rst, self._rev)
            self.results["return_rate"] = _safe_div(returns_val, rev)

        # refund_rate
        if "refund_rate" in self.derivable:
            refund_val = _col_val(df_rst, self._refund)
            rev = _col_val(df_rst, self._rev)
            self.results["refund_rate"] = _safe_div(refund_val, rev)

        # revenue_concentration_score (HHI by product)
        if "revenue_concentration_score" in self.derivable and self._prod_name:
            prod_rev = _groupby_sum(df_rst, self._prod_name, self._rev)
            if prod_rev is not None and len(prod_rev) > 0 and prod_rev.sum() > 0:
                shares = prod_rev / prod_rev.sum()
                self.results["revenue_concentration_score"] = float((shares ** 2).sum())

        # profit_concentration_score (HHI by product)
        if "profit_concentration_score" in self.derivable and self._prod_name:
            prod_prof = _groupby_sum(df_rst, self._prod_name, self._profit)
            if prod_prof is not None and len(prod_prof) > 0 and prod_prof.sum() > 0:
                shares = prod_prof / prod_prof.sum()
                self.results["profit_concentration_score"] = float((shares ** 2).sum())

        # seasonal_demand_score (ratio of peak to trough monthly revenue)
        if "seasonal_demand_score" in self.derivable and self.date_col:
            s = _resample_series(self.df, self.date_col, self._rev, "ME")
            if s is not None and len(s) > 1 and s.min() > 0:
                self.results["seasonal_demand_score"] = float(s.max() / s.min())

        # peak_sales_month / lowest_sales_month
        if self.date_col:
            s = _resample_series(self.df, self.date_col, self._rev or self._sales, "ME")
            if s is not None and len(s) > 0:
                if "peak_sales_month" in self.derivable:
                    self.results["peak_sales_month"] = str(s.idxmax().strftime("%Y-%m")) if hasattr(s.idxmax(), 'strftime') else str(s.idxmax())
                    self.results["peak_sales_month_value"] = float(s.max())
                if "lowest_sales_month" in self.derivable:
                    self.results["lowest_sales_month"] = str(s.idxmin().strftime("%Y-%m")) if hasattr(s.idxmin(), 'strftime') else str(s.idxmin())
                    self.results["lowest_sales_month_value"] = float(s.min())


# ──────────────────────────────────────────────
# Public convenience function
# ──────────────────────────────────────────────

def calculate_metrics(
    df: pd.DataFrame,
    date_col: Optional[str],
    mappings: Dict[str, Any],
    derivable_metrics: List[str],
    timeframes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Convenience function: calculate all derivable financial metrics.

    Parameters
    ----------
    df : pd.DataFrame
        Standardized DataFrame.
    date_col : str or None
        Name of the date column.
    mappings : dict
        Column mappings from LLM analysis.
    derivable_metrics : list[str]
        List of derivable metric names.
    timeframes : list[str] or None
        Available timeframes.

    Returns
    -------
    dict
        Flat dictionary of metric_name → value.
    """
    calc = MetricsCalculator(df, date_col, mappings, derivable_metrics, timeframes)
    return calc.calculate_all()
