OpenFin

Agent 2 subAgent 2

Key objective : Generate a comprehensive, data-backed response to the user's prompt

________________________________________________________________________________________________________________________________________

Key functionalities :

    Response generation :

        Receive structured context from subAgent 1 containing prompt, analysis metadata, and retrieved data. Use a single LLM call to formulate a clear, accurate, and actionable response.

    Multi-source awareness :

        Handle data from all four source types:
        - filtered-data: Numerical metrics and specific field values
        - base-reports: Extracted PDF report sections (narrative analysis)
        - insights: Extracted PDF insight sections (issue analysis, research)
        - internet: Tavily web search results

        Properly cite data sources in the response.

    Insufficient data handling :

        When data is missing or insufficient (null values, empty sections, or no data found), inform the user honestly about what is and isn't available, and suggest what data would be needed.

    Conflicting data handling :

        When data sources present conflicting information, note discrepancies and present a balanced analysis to the user.

    Professional tone :

        Write responses in a professional financial advisory tone suitable for business stakeholders. Include specific numbers when available, note data limitations transparently, and provide actionable insights.

    Main run function :

        Receive subAgent 1's structured context, generate response via LLM, and return the final response to Agent 2 for delivery to the user. Designed to complete in 1-2 LLM calls.

    Activity log :

        Maintain main/Agent2/subAgent2/log.txt with current activity only (no past activity).
        Activities: "analyzing context", "generating response", "idle"

Key notes :

    subAgent must complete its functionality in 1-2 LLM calls.

    subAgent must handle all data source types and format responses appropriately for each.

    subAgent must be transparent about data limitations — never fabricate or guess numbers.

    subAgent operates on the structured output from subAgent 1.

________________________________________________________________________________________________________________________________________

Pipeline

    Main run function initiated with subAgent 1's structured context
    - Context analyzed to determine response approach
    - LLM call generates the final response based on data and prompt
    - Response returned to Agent 2 for delivery to user
