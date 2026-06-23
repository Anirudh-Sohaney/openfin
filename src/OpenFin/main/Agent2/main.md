# main.py

## Key Objective
Orchestrate Agent 2's pipeline: receive a user prompt, coordinate subAgent 1 (data analysis) and subAgent 2 (response generation), maintain conversation memory across 2-4 exchanges, and return a plain string answer.

## Tools / Algorithms Used
- **subAgent 1** (`subAgent1.main.run`): Analyzes prompt and retrieves data from filtered-data JSONs, base-report PDFs, insight PDFs, or Tavily internet search.
- **subAgent 2** (`subAgent2.main.run`): Generates a professional financial advisory response via a single LLM call.
- **ConversationMemory**: Sliding-window history (up to 4 exchanges) that formats previous Q&A into the LLM prompt for context continuity.
- **Activity log**: Timestamped logging to `log.txt` for Agent 2's active tracking.

## Key Objects

### `run(prompt: str) -> str`
- **Parameters**: `prompt` - User's natural-language question.
- **Use**: Main entry point. Runs the full pipeline:
  1. subAgent 1 analyzes the prompt and retrieves data
  2. Injects conversation history into the data dict
  3. subAgent 2 generates the final response
  4. Stores exchange in sliding-window memory
  5. Returns answer string (with caveats appended if present)

### `ConversationMemory`
- **Parameters**: `max_exchanges` (default 4) - Maximum conversation turns to remember.
- **Use**: Maintains a sliding window of recent exchanges. Each exchange stores prompt, answer, and source metadata. The `get_context()` method formats history for inclusion in the LLM prompt.

### `reset_memory()`
- **Use**: Clears conversation history for a fresh start.

### `get_memory_size() -> int`
- **Use**: Returns the number of stored exchanges.

## Data Flow

```
User prompt (string)
  │
  ▼
Agent 2 Orchestrator (main.py)
  │
  ├── subAgent 1: analyze_prompt()
  │   │             → data_source, keywords, required_fields
  │   └── retrieve_data()
  │                 → metrics, specific_fields, content, sections
  │
  ├── Inject conversation_history (if available)
  │
  ├── subAgent 2: generate_response()
  │                 → LLM call → { answer, caveats }
  │
  └── Return: answer string (+ caveats if present)
  │
  ▼
Final response sent to user
```
