import os
import json
from datetime import datetime
from typing import Dict, Any

from .prompt_analyzer import analyze_prompt
from .data_retriever import retrieve_data

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


def run(user_prompt: str) -> Dict[str, Any]:
    try:
        _log("parsing prompt")
        analysis = analyze_prompt(user_prompt)

        _log("retrieving data")
        data = retrieve_data(analysis)

        _log("assembling context")
        result = {
            "prompt": user_prompt,
            "analysis": {
                "data_source": analysis.get("data_source"),
                "data_keywords": analysis.get("data_keywords"),
                "required_data_fields": analysis.get("required_data_fields"),
                "tavily_query": analysis.get("tavily_query"),
                "summary": analysis.get("summary", ""),
            },
            "data": {
                "source": data.get("source"),
                "source_type": data.get("source_type"),
                "metrics": data.get("metrics", {}),
                "specific_fields": data.get("specific_fields", {}),
                "content": data.get("content"),
                "relevant_sections": data.get("relevant_sections", []),
            },
        }

        _log("idle")
        return result

    except Exception as e:
        _log("idle")
        import traceback
        traceback.print_exc()
        return {
            "prompt": user_prompt,
            "error": str(e),
            "analysis": {},
            "data": {},
        }


if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "what is my annual revenue thus far?"
    result = run(prompt)
    print(json.dumps(result, indent=2, default=str))
