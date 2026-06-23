OpenFin

Agent 2 subAgent 1

Key objective : Analyze user prompt and retrieve required data for subAgent 2

________________________________________________________________________________________________________________________________________

Key functionalities :

    Prompt analysis :

        Use LLM to parse the intent of the user prompt and determine what data is needed. Identify which data sources to consult: filtered-data, base reports, insights, or online research (Tavily).

    Data retrieval :

        Given the identified target, retrieve data from the proper destination (local file or Tavily internet research). Handle varied prompts including ambiguous, complex, or multi-part questions.

    Insufficient data handling :

        Account for missing or incomplete data by noting gaps and limitations when data is not found in any source.

    Context assembly :

        Assemble retrieved data into a structured context for subAgent 2 to consume, including prompt metadata and all data found across sources.

    Main run function :

        Take a user prompt, run it through prompt analysis, retrieve data from the identified destination, assemble into structured context, and return to subAgent 2. Designed to complete in under 2 LLM calls.

    Activity log :

        Maintain main/Agent2/subAgent1/log.txt with current activity only (no past activity).
        Activities: "parsing prompt", "retrieving data", "assembling context", "idle"

Key notes :

    subAgent must be largely LLM-based but designed to complete its functionalities in under 2 LLM calls.

    subAgent must handle a wide variety of prompts from simple questions to complex multi-part analyses.

    subAgent operates primarily on data from main/data/filtered-data, main/reports/base-reports, main/reports/insights, and online research via Tavily.

________________________________________________________________________________________________________________________________________

Pipeline

    Main run function initiated with user prompt
    - Prompt analyzed via LLM for target data sources
    - Data retrieved from identified destination(s)
    - Retrieved data assembled into structured context
    - Structured context returned to subAgent 2
