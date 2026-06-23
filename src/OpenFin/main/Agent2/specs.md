OpenFin Agent 2

Agent 2 key objective :

    - Receive user prompt
    - Analyze data and insight
    - Provide user with an adequate response

________________________________________________________________________________________________________________________________________

Key structure :

Agent 2 :

    Function : Serve as a chatbot and financial advisor to the user, providing quick answers based on data or insights.

    Main pipeline :

        - Initiated through a key function with a prompt parameter
        - Initiate subAgent 1 (prompt analysis)
        - Initiate subAgent 2 (response generation)

    Key notes :

        - Agent 2 does not execute any LLM calls; it only initiates subAgents
        - Agent 2 must maintain active tracking of its subAgents' activity
        - Agent must have a 2-4 message memory (must be able to continue a conversation for 2-4 exchanges with good memory and context)

        Example situation :

            - User : "what is my highest earning product?"

            - subAgent 1 identifies prompt requires revenue, sales, and/or product data
            - subAgent 1 retrieves data and initiates subAgent 2 with the information
            - subAgent 2 : "Your highest earning product is ..."



