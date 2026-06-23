OpenFin

Agent 1 subAgent 1

Key objective : Process documents into analysis metrics

________________________________________________________________________________________________________________________________________

Key functionalities :

    Diverse data acceptance :

        Accept all spreadsheet formats and translate them to analyzable data (Python matrix/variables).

    Brief data analysis :

        Feed information about the data (variable types, value types, etc.) to the LLM. The LLM identifies what values can and should be derived.

    Value derivation :

        After receiving feedback from the LLM, break down the uploaded data into all potentially useful metrics such as:

            total_revenue, yearly_revenue, quarterly_revenue, monthly_revenue, revenue_growth, yearly_revenue_growth, quarterly_revenue_growth, monthly_revenue_growth, total_sales, yearly_sales, quarterly_sales, monthly_sales, sales_growth, average_order_value, total_units_sold, highest_selling_product, lowest_selling_product, highest_revenue_product, lowest_revenue_product, highest_profit_product, lowest_profit_product, highest_margin_product, lowest_margin_product, gross_profit, net_profit, operating_profit, gross_margin, net_margin, operating_margin, profit_growth, inventory_value, inventory_turnover, inventory_turnover_days, average_inventory_age, inventory_expenses, monthly_inventory_expenses, quarterly_inventory_expenses, yearly_inventory_expenses, inventory_carrying_cost, overstocked_inventory_value, understocked_inventory_value, slowest_moving_product, fastest_moving_product, total_expenses, monthly_expenses, quarterly_expenses, yearly_expenses, expense_growth, expense_to_revenue_ratio, payroll_expenses, payroll_to_revenue_ratio, revenue_per_employee, profit_per_employee, accounts_receivable, overdue_receivables, average_collection_period, accounts_payable, average_payment_period, operating_cashflow, net_cashflow, free_cashflow, cash_reserves, cash_burn_rate, cash_runway, customer_count, customer_growth_rate, customer_retention_rate, repeat_purchase_rate, average_customer_value, largest_customer_revenue_share, supplier_count, supplier_concentration, supplier_dependency_score, largest_supplier_spend, supplier_cost_growth, seasonal_demand_score, peak_sales_month, lowest_sales_month, product_profitability_score, product_growth_rate, margin_compression_rate, revenue_concentration_score, profit_concentration_score, customer_concentration_score, return_rate, refund_rate, discount_rate, marketing_spend, marketing_roi, shipping_costs, logistics_cost_ratio, fixed_costs, variable_costs, debt_to_equity_ratio, current_ratio, quick_ratio, working_capital, return_on_assets, return_on_equity, return_on_investment, asset_turnover_ratio, gross_profit_per_product, net_profit_per_product, break_even_point, operating_leverage, financial_leverage

    Proper data allocation :

        After deriving values and metrics, allocate them against existing data (new revenue data replaces old revenue metrics, etc.).

    Main run function :

        Retrieve data from main/data/uploaded-data, run it through the analysis process, and save to main/data/filtered-data.

    Activity log :

        Maintain main/Agent1/subAgent1/log.txt with current activity only (no past activity).
        Activities: "breaking down data" or "idle"

Key notes :

    For value derivation, metrics are calculated across applicable timeframes based on available new data and prior broken-down data. Possible timeframes:

        3 months, 6 months, 12 months, 24 months, 36 months

________________________________________________________________________________________________________________________________________

Pipeline

    Main run function initiated
    - Data retrieved, converted into Python matrix and variables
    - Data characteristics reported to LLM; LLM reports back on what metrics can be generated and how
    - Metrics are generated
    - Metrics are properly allocated and saved to main/data/filtered-data
