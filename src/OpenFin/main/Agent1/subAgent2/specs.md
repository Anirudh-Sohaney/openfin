OpenFin

Agent 1 subAgent 2

Key objective : Develop basic financial reports using base metrics

________________________________________________________________________________________________________________________________________

Key functionalities :

    Possible reports identification :

        Based on available metrics, prompt the LLM to identify what reports can be generated.

    Generate report :

        Iterate through the potential reports identified by the LLM, reprompting the LLM to generate each report with the necessary metrics.

    Properly interpret and organize report :

        Report must have clear division of sections. Each section expects a header with content.

        Final format: {"Report Name": {"section_heading": "section content"}}

        Report name must describe the type of report.

        Reports must be saved as JSON in main/Agent1/base-gens.

    Activity log :

        Maintain main/Agent1/subAgent2/log.txt with current activity only (no past activity).
        Activities: "thinking", "generating report for {name}", "idle"

Key notes :

    Minimum required sections per report: Data, Analysis, Conclusion. More sections are expected depending on report type.

    Ideal reports to generate:
        Executive Financial Summary, Revenue, Sales, Profit & Loss, Expense, Cash Flow, Inventory, Product Performance, Supplier, Customer, Accounts Receivable, Accounts Payable, Payroll, Financial Health, Business Growth

    When the LLM returns possible reports, filter out reports that already exist UNLESS the associated metrics have changed.

________________________________________________________________________________________________________________________________________

Pipeline

    Main run function initiated
    - LLM identifies potential reports from current data availability in main/data/filtered-data
    - Existing reports filtered out
    - LLM reprompted for each report, fed with required metrics
    - Reports structured properly and saved in main/Agent1/base-gens



