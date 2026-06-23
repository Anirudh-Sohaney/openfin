OpenFin

Agent 1 subAgent 3

Key objective : Conduct online research

________________________________________________________________________________________________________________________________________

Key functionalities :

    Online research :

        Assess metrics and compare online using the LLM with Tavily API to find better solutions for improving profitability.

    Proper report :

        The LLM's response must be structured as a professional report with clear subdivisions, headings, and content.

        Format: {"Report Name": {"section_heading": "section content"}}

        Each report JSON must be saved in main/Agent1/insight-gens.

        Each report must include a professional introduction, supporting evidence/data, and thorough detail of online research.

    Activity log :

        Maintain main/Agent1/subAgent3/log.txt with current activity only (no past activity).
        Activities: "researching online", "comparing suppliers", "researching products", "analyzing", "generating report", "idle"

Key notes :

    The main target of this subAgent is to identify solutions centered on increasing business profit.

    Work by observing key metrics (top-selling product, biggest supplier, etc.) and finding online solutions such as:

        alternative_suppliers, lower_supplier_pricing, better_supplier_terms, supplier_dependency_risks, emerging_high_demand_products, declining_product_categories, seasonal_market_trends, competitor_pricing_trends, industry_profit_margin_benchmarks, industry_expense_benchmarks, inventory_optimization_opportunities, pricing_optimization_opportunities, customer_retention_opportunities, revenue_diversification_opportunities, cost_reduction_opportunities, automation_opportunities, operational_efficiency_improvements, cash_flow_optimization_strategies, new_sales_channel_opportunities, geographic_expansion_opportunities

    Ensure proper implementation of Tavily API for deep internet research.

    Skip solutions that already have existing reports in main/Agent1/insight-gens.

________________________________________________________________________________________________________________________________________

Pipeline

    Main run function initiated
    - Identify relevant metrics from main/data/filtered-data
    - Feed LLM with the relevant metrics and conduct Tavily research
    - Filter out solutions with existing reports
    - Generate professional report for each new solution
    - Save report JSONs in main/Agent1/insight-gens
