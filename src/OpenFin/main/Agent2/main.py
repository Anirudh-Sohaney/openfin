"""
Agent 2 — Financial Advisor and Chatbot Orchestrator

Key pipeline:
  1. Receive user prompt
  2. subAgent 1: Analyze prompt & retrieve data
  3. subAgent 2: Generate response from data
  4. Maintain 2-4 exchange conversation memory
  5. Return answer as a string

Usage:
    from main.Agent2.main import run
    answer = run("what is my annual revenue?")
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# ── Ensure project root is on the path for subAgent imports ─────────────
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
import sys
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from main.Agent2.subAgent1.main import run as _subagent1_run
from main.Agent2.subAgent2.main import run as _subagent2_run

LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")


# ── Activity logging ────────────────────────────────────────────────────

def _log(message: str):
    """Append a timestamped line to Agent 2's activity log."""
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except OSError:
        print(line, end="")


# ── Conversation Memory ─────────────────────────────────────────────────

class ConversationMemory:
    """Stores up to N exchanges of conversation history for context continuity.

    Each exchange stores: prompt (user question), answer (advisor response),
    and source_info (which data source was used). The memory is trimmed to
    `max_exchanges` entries (default 4) by removing the oldest exchanges.
    """

    def __init__(self, max_exchanges: int = 4):
        self.max_exchanges = max_exchanges
        self.history: List[Dict[str, Any]] = []

    def add_exchange(self, prompt: str, answer: str,
                     source_info: Optional[Dict] = None):
        """Record a completed exchange."""
        self.history.append({
            "prompt": prompt,
            "answer": answer,
            "source_info": source_info or {},
        })
        # Trim to the most recent N exchanges (sliding window)
        if len(self.history) > self.max_exchanges:
            self.history = self.history[-self.max_exchanges:]

    def get_context(self) -> str:
        """Return formatted conversation history for the LLM prompt.

        Returns an empty string if no history exists yet.
        """
        if not self.history:
            return ""
        lines = ["Previous conversation (for context):"]
        for i, ex in enumerate(self.history):
            answer_preview = ex["answer"][:300] + "..." if len(ex["answer"]) > 300 else ex["answer"]
            lines.append(f"  [{i+1}] User: {ex['prompt']}")
            lines.append(f"      Advisor: {answer_preview}")
            if ex.get("source_info"):
                si = ex["source_info"]
                src = si.get("data_source") or si.get("source_type") or "unknown"
                lines.append(f"      (source: {src})")
        return "\n".join(lines)

    def clear(self):
        """Reset conversation memory."""
        self.history = []


# ── Global memory instance ──────────────────────────────────────────────
# This persists across calls within the same session, enabling multi-turn
# conversations with context.
_memory = ConversationMemory(max_exchanges=4)


def run(prompt: str) -> str:
    """Main entry point for Agent 2 — the financial advisor chatbot.

    Args:
        prompt: The user's question (e.g., "what is my annual revenue?").

    Returns:
        A professional, data-backed answer as a plain string.
        If there are caveats (missing data, source notes), they are appended
        after a separator.
    """
    # Guard against empty prompts
    if not prompt or not prompt.strip():
        _log("START (empty prompt)")
        return (
            "I didn't receive a question. Please ask me anything about your "
            "financial data, reports, or business insights, and I'll help you."
        )

    _log(f"START prompt: '{prompt[:120]}'")
    start_time = time.time()

    try:
        # ── Step 1: subAgent 1 — Analyze prompt & retrieve data ──────
        _log("  → subAgent 1: analyzing prompt & retrieving data ...")
        subagent1_start = time.time()
        s1_result = _subagent1_run(prompt)
        s1_elapsed = time.time() - subagent1_start
        _log(f"  ← subAgent 1 done: "
             f"source={s1_result.get('analysis', {}).get('data_source')}, "
             f"{s1_elapsed:.1f}s")

        # ── Step 2: Inject conversation history ──────────────────────
        conversation_context = _memory.get_context()
        if conversation_context:
            s1_result["conversation_history"] = conversation_context
            _log(f"  → Injected conversation history ({len(_memory.history)} prior exchanges)")

        # ── Step 3: subAgent 2 — Generate response ───────────────────
        _log("  → subAgent 2: generating response via LLM ...")
        subagent2_start = time.time()
        s2_result = _subagent2_run(s1_result)
        s2_elapsed = time.time() - subagent2_start
        _log(f"  ← subAgent 2 done: {s2_elapsed:.1f}s")

        # ── Step 4: Extract the answer ───────────────────────────────
        answer = s2_result.get("response", {}).get("answer", "")
        caveats = s2_result.get("response", {}).get("caveats", "")
        source_info = s2_result.get("source_info", {})

        # ── Step 5: Store in conversation memory ─────────────────────
        _memory.add_exchange(prompt, answer, source_info)

        elapsed = time.time() - start_time
        _log(f"END total: {elapsed:.1f}s, answer={len(answer)} chars, "
             f"caveats={len(caveats)} chars")

        # ── Step 6: Return answer (with caveats appended) ────────────
        if caveats and caveats.strip():
            return f"{answer}\n\n---\n{caveats}"
        return answer

    except Exception as e:
        elapsed = time.time() - start_time
        _log(f"ERROR after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return (
            "I apologize, but I encountered an error while processing your "
            "request. Please try again or rephrase your question. "
            f"If the problem persists, check that your API keys and "
            f"dependencies are properly configured. (Error: {e})"
        )


def reset_memory():
    """Clear the conversation memory (start fresh)."""
    _memory.clear()
    _log("Conversation memory reset")


def get_memory_size() -> int:
    """Return the number of exchanges currently stored in memory."""
    return len(_memory.history)


# ── CLI entry point for quick testing ───────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "what is my annual revenue?"
    result = run(prompt)
    print(result)
