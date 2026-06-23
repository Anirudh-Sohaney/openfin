import os
import json
from datetime import datetime
from typing import Dict, Any

from .response_generator import generate_response

LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")


def _log(message: str):
    """Write a single line to the activity log.

    Overwrites the file each time so it shows only the current/latest activity
    (no past activity), as required by the spec.
    """
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {message}\n"
    try:
        with open(LOG_FILE, "w") as f:
            f.write(line)
    except OSError:
        print(line, end="")


def run(subagent1_result: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for subAgent 2.

    Takes the structured output from subAgent 1 and generates a
    professional financial advisory response to the user's prompt.

    Args:
        subagent1_result: Dict from subAgent 1 with keys:
            - prompt: The user's original question
            - analysis: Analysis metadata (data_source, keywords, fields, summary)
            - data: Retrieved data (metrics, specific_fields, content, sections)

    Returns:
        Dict with keys:
            - prompt: Original user prompt
            - response: Dict with answer and caveats from the LLM
            - source_info: Metadata about the data source used
    """
    user_prompt = subagent1_result.get("prompt", "")

    # Guard against empty prompts
    if not user_prompt.strip():
        _log("idle")
        return {
            "prompt": user_prompt,
            "response": {
                "answer": (
                    "I didn't receive a question. Please ask me anything about your "
                    "financial data, reports, or business insights, and I'll help you."
                ),
                "caveats": "",
            },
            "source_info": {
                "data_source": None,
                "source_type": None,
                "source": None,
            },
        }

    try:
        _log("analyzing context")
        _log("generating response")
        response = generate_response(subagent1_result)

        _log("idle")

        return {
            "prompt": user_prompt,
            "response": {
                "answer": response.get("answer", ""),
                "caveats": response.get("caveats", ""),
            },
            "source_info": {
                "data_source": subagent1_result.get("analysis", {}).get("data_source"),
                "source_type": subagent1_result.get("data", {}).get("source_type"),
                "source": subagent1_result.get("data", {}).get("source"),
            },
        }

    except Exception as e:
        _log("idle")
        import traceback
        traceback.print_exc()
        return {
            "prompt": user_prompt,
            "response": {
                "answer": (
                    "I apologize, but I encountered an error while generating your response. "
                    "Please try again or rephrase your question."
                ),
                "caveats": f"Error: {str(e)}",
            },
            "source_info": {
                "data_source": None,
                "source_type": None,
                "source": None,
            },
            "error": str(e),
        }


if __name__ == "__main__":
    import sys

    # Accept JSON input from stdin or command line
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        raw = sys.stdin.read().strip()
        if raw:
            subagent1_result = json.loads(raw)
        else:
            print("Error: No JSON input provided via stdin.", file=sys.stderr)
            sys.exit(1)
    else:
        # Default test input
        subagent1_result = {
            "prompt": "what is my annual revenue?",
            "analysis": {
                "data_source": "filtered-data",
                "data_keywords": ["revenue"],
                "required_data_fields": ["total_revenue", "yearly_revenue"],
                "tavily_query": None,
                "summary": "User wants to know their annual revenue",
            },
            "data": {
                "source": "test_file.json",
                "source_type": "filtered_data",
                "metrics": {"total_revenue": 175000.0, "yearly_revenue": 175000.0},
                "specific_fields": {"total_revenue": 175000.0, "yearly_revenue": 175000.0},
                "content": {},
                "relevant_sections": [],
            },
        }

    result = run(subagent1_result)
    print(json.dumps(result, indent=2, default=str))
