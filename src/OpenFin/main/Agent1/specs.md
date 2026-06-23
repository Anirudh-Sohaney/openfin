OpenFin Agent 1

Agent 1 key objective :

    - Receive data
    - Generate base reports
    - Analyze for potential missed profits

________________________________________________________________________________________________________________________________________

Key structure :

Agent 1 :

    Function : Initiate subAgents sequentially upon detecting data upload.

    Main pipeline :

        - Initiated through a key function
        - Initiate subAgent 1 and wait until subAgent1/log.txt shows "idle"
        - Initiate subAgent 5's start observations (watches base-gens and insight-gens)
        - Run subAgents 2, 3, and 4 in parallel
        - subAgent 2 saves JSON reports to main/Agent1/base-gens
        - subAgents 3 and 4 save JSON reports to main/Agent1/insight-gens
        - subAgent 5 picks up JSONs from base-gens and insight-gens, converts to PDFs, saves to main/reports/
        - Wait until subAgents 2, 3, 4, and 5 show "idle" in their respective log.txt
        - End subAgent 5's observations

    Key notes :

        - Agent 1 does not execute any LLM calls; it only initiates subAgents
        - Agent 1 must properly queue tasks for subAgents in case of rapid file uploads
        - Agent 1 must maintain an active log of each subAgent

        Example situation :

            - User uploads data_set_1.csv, then immediately uploads data_set_2.csv and data_set_3.csv

            Active log :
                Agent 1 : queued - data_set_3.csv
                subAgent 1 : processing data_set_2.csv
                subAgent 2 : idle
                subAgents 3 and 4 : analyzing data_set_1.csv
                subAgent 5 : generating PDF for data_set_1.csv reports
    

