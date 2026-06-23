OpenFin

Agent 1 subAgent 4

Key objective : Identify financial leaks and gaps in finances

________________________________________________________________________________________________________________________________________

Key functionalities :

    Financial inefficiencies analysis :

        Analyze metrics and trends from subAgent 1 to identify critical financial issues and inefficiencies that are costing the user profit.

        Use the LLM to analyze the variables and detect issues such as:

            declining_revenue, slowing_revenue_growth, declining_profit, slowing_profit_growth, margin_compression, excessive_expense_growth, expenses_growing_faster_than_revenue, declining_cash_flow, low_cash_reserves, high_cash_burn_rate, increasing_accounts_receivable, overdue_customer_payments, poor_collection_efficiency, increasing_accounts_payable, supplier_dependency_risk, customer_dependency_risk, revenue_concentration_risk, profit_concentration_risk, declining_inventory_turnover, excess_inventory_levels, overstocked_products, understocked_products, slow_moving_inventory, dead_inventory, declining_product_sales, declining_product_profitability, underperforming_products, excessive_inventory_carrying_costs, rising_supplier_costs, excessive_payroll_costs, payroll_growing_faster_than_revenue, declining_revenue_per_employee, declining_profit_per_employee, declining_customer_retention, declining_repeat_purchase_rate, seasonal_inventory_mismatch, declining_average_order_value, high_refund_rates, excessive_discounting, declining_gross_margin, declining_net_margin, declining_operating_margin, inventory_growth_exceeding_sales_growth, poor_working_capital_management, supplier_concentration_risk, customer_concentration_risk, high_operating_costs, declining_financial_health, volatile_revenue_streams, volatile_profitability, inefficient_product_mix, low_margin_high_volume_products, high_margin_low_volume_products, cash_flow_bottlenecks, poor_inventory_management, underperforming_sales_periods, declining_business_growth, reduced_market_demand, declining_product_lifecycle, inefficient_resource_allocation, excessive_fixed_costs, poor_return_on_investment, poor_return_on_assets, poor_return_on_equity, declining_operational_efficiency, unsustainable_growth_patterns, increasing_financial_risk

    Report generation :

        After identifying issues, use the LLM to convert findings into professional reports.

        Format: {"Report Name": {"section_heading": "section content"}}

        Reports must contain proper instructions, data backing the findings, detailed explanations, and professional advice on solutions.

        Reports must be saved as JSON files in main/Agent1/insight-gens.

    Activity log :

        Maintain main/Agent1/subAgent4/log.txt with current activity only (no past activity).
        Activities: "assessing issues" or "idle"

Key notes :

    Skip issues that already have existing reports in main/Agent1/insight-gens.

________________________________________________________________________________________________________________________________________

Pipeline

    Main run function initiated
    - LLM identifies potential issues from metrics in main/data/filtered-data
    - Identified issues filtered against existing reports in main/Agent1/insight-gens
    - Professional report generated for each new issue
    - Reports saved as JSON in main/Agent1/insight-gens
