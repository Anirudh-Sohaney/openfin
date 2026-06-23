import os
import json
import re
from typing import Dict, Any
from main.llm_client import get_llm_client, get_model



def _strip_json_fences(content: str) -> str:
    """Remove markdown code fences and whitespace from LLM response."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[-1].strip() == "```":
            content = "\n".join(lines[1:-1])
        else:
            content = "\n".join(lines[1:])
    return content.strip()


def _parse_json_response(content: str) -> Dict:
    """Parse LLM response as JSON, with regex fallback."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"LLM returned invalid JSON: {content[:500]}")


def _format_metrics(metrics: Dict, max_items: int = 30) -> str:
    """Format metrics dict for LLM prompt, respecting token budget."""
    if not metrics:
        return "(no metrics available)"

    items = []
    for k, v in sorted(metrics.items()):
        if v is None:
            items.append(f"  {k}: NOT AVAILABLE (null)")
        elif isinstance(v, float):
            # Format whole-number floats cleanly, otherwise show 2 decimals
            if v == int(v) and abs(v) < 1e12:
                items.append(f"  {k}: {int(v):,}")
            else:
                items.append(f"  {k}: {v:,.2f}")
        elif isinstance(v, int):
            items.append(f"  {k}: {v:,}")
        elif isinstance(v, str) and len(v) > 150:
            items.append(f"  {k}: {v[:150]}...")
        elif isinstance(v, dict):
            items.append(f"  {k}: {{... {len(v)} entries}}")
        elif isinstance(v, list):
            items.append(f"  {k}: [... {len(v)} items]")
        else:
            items.append(f"  {k}: {v}")

        if len(items) >= max_items:
            remaining = len(metrics) - max_items
            if remaining > 0:
                items.append(f"  ... and {remaining} more metrics")
            break

    return "\n".join(items) if items else "(no metrics available)"


def _format_relevant_sections(sections: list) -> str:
    """Format relevant_sections list for LLM prompt."""
    if not sections:
        return "(no relevant sections found)"

    lines = []
    for i, sec in enumerate(sections):
        heading = sec.get("heading", f"Section {i+1}")
        content = sec.get("content", "")
        # Ensure content is a string for consistent formatting
        if not isinstance(content, str):
            content = str(content)
        if len(content) > 2000:
            content = content[:2000] + "..."
        lines.append(f"  [{heading}]")
        lines.append(f"  {content}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_tavily_results(results: list) -> str:
    """Format Tavily search results for LLM prompt."""
    if not results:
        return "(no search results)"

    lines = []
    for i, r in enumerate(results):
        title = r.get("title", f"Result {i+1}")
        url = r.get("url", "N/A")
        content = r.get("content", "")
        if isinstance(content, str) and len(content) > 1500:
            content = content[:1500] + "..."
        lines.append(f"  Result {i+1}: {title}")
        lines.append(f"  URL: {url}")
        lines.append(f"  {content}")
        lines.append("")
    return "\n".join(lines).strip()


def build_response_prompt(subagent1_result: Dict[str, Any]) -> str:
    """Build the LLM prompt for generating a financial advisor response.

    Adapts the prompt structure based on the data source type
    (filtered-data, base-reports, insights, internet, or no_data_found).
    Also includes conversation history from previous exchanges if available.
    """
    user_prompt = subagent1_result.get("prompt", "")
    analysis = subagent1_result.get("analysis", {})
    data = subagent1_result.get("data", {})
    conversation_history = subagent1_result.get("conversation_history", "")

    data_source = analysis.get("data_source", "unknown")
    source_type = data.get("source_type", "unknown")
    user_summary = analysis.get("summary", "")

    # Extract and format data for the prompt
    metrics = data.get("metrics", {})
    specific_fields = data.get("specific_fields", {})
    content = data.get("content", {})
    relevant_sections = data.get("relevant_sections", [])
    source_name = data.get("source", "unknown")

    # Identify missing fields
    missing_fields = [k for k, v in specific_fields.items() if v is None]
    available_fields = {k: v for k, v in specific_fields.items() if v is not None}

    # Format each data component
    metrics_formatted = _format_metrics(metrics)
    fields_formatted = json.dumps(specific_fields, indent=2, default=str) if specific_fields else "(none)"
    sections_formatted = _format_relevant_sections(relevant_sections)

    # Determine if we have Tavily results
    has_tavily = source_type == "tavily"
    tavily_query = analysis.get("tavily_query", "")

    # Build the prompt based on source type
    if source_type == "no_data_found":
        data_section = (
            "DATA: No relevant data was found in any of the available sources "
            "(filtered metrics, base reports, insights, or internet search). "
            "Suggest what data or reports the user would need to upload "
            "or generate in order to answer this question properly."
        )
    elif has_tavily:
        tavily_formatted = _format_tavily_results(relevant_sections)
        data_section = (
            f"DATA SOURCE: Internet search via Tavily\n"
            f"Original search query: {tavily_query}\n"
            f"\nSEARCH RESULTS:\n{tavily_formatted}"
        )
    elif source_type in ("pdf_report",):
        data_section = (
            f"DATA SOURCE: {source_name} (professional PDF report)\n"
            f"Source type: {source_type}\n"
            f"\nRELEVANT REPORT SECTIONS:\n{sections_formatted}"
        )
    elif source_type in ("filtered_data", "combined_filtered_data"):
        data_section = (
            f"DATA SOURCE: {source_name} (structured financial metrics)\n"
            f"Source type: {source_type}\n"
            f"\nSPECIFIC REQUESTED FIELDS:\n{fields_formatted}\n"
            f"\nAVAILABLE METRICS:\n{metrics_formatted}"
        )
    else:
        # Generic fallback
        data_section = (
            f"DATA SOURCE: {source_name}\n"
            f"Source type: {source_type}\n"
            f"\nSPECIFIC FIELDS:\n{fields_formatted}\n"
            f"\nMETRICS:\n{metrics_formatted}\n"
            f"\nRELEVANT SECTIONS:\n{sections_formatted}"
        )

    missing_info = ""
    if missing_fields:
        mf_list = ", ".join(missing_fields)
        missing_info = (
            f"\n**IMPORTANT — MISSING DATA**: The following fields were requested "
            f"but are NOT available in the data: {mf_list}. "
            f"Do NOT fabricate values for these fields. Clearly inform the user "
            f"that this data is unavailable."
        )

    # Build conversation history section
    conversation_section = ""
    if conversation_history:
        conversation_section = (
            "\nCONVERSATION HISTORY:\n"
            f"{conversation_history}\n"
            "Use this context to continue the conversation naturally. "
            "Reference previous answers if the user is asking a follow-up.\n"
        )

    prompt = f"""You are a professional financial advisor for OpenFin, a financial analysis platform.
Your task is to answer the user's question based on the data provided.

USER QUESTION: "{user_prompt}"

INTENT SUMMARY: {user_summary}

{data_section}
{conversation_section}
{missing_info}

RESPONSE RULES:
1. **Tone**: Professional, objective, and advisory. Address the user directly.
2. **Evidence-based**: Use ONLY the data provided above. Reference specific numbers when available.
3. **Transparency**: If data is missing or insufficient, clearly state what is unavailable and why the question cannot be fully answered.
4. **Actionable**: Provide practical insights or recommendations where the data supports them.
5. **No fabrication**: Never invent numbers, metrics, or data points. If you don't have the data, say so honestly.
6. **Structure**: Organize your response clearly. Use natural paragraph flow — do not use JSON-like keys or bullet-heavy formatting within the answer itself.

Return a JSON object with exactly these two keys:

{{
    "answer": "Your comprehensive, well-structured response to the user's question.",
    "caveats": "Any data limitations, missing fields, sourcing notes, or caveats. Leave as empty string if none."
}}

Return ONLY valid JSON, no markdown fences or other text.
"""

    return prompt


def generate_response(subagent1_result: Dict[str, Any]) -> Dict[str, str]:
    """Generate a financial advisor response using a single LLM call.

    Args:
        subagent1_result: The full result dict from subAgent 1, containing
            prompt, analysis, and data keys.

    Returns:
        Dict with keys:
            - answer: The LLM-generated response text
            - caveats: Data limitation notes (or empty string)
    """
    model = get_model()
    prompt = build_response_prompt(subagent1_result)

    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional financial advisor for OpenFin. "
                    "You return only valid JSON with two keys: 'answer' and 'caveats'. "
                    "You are honest about data limitations. You never fabricate numbers."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2500,
    )

    content = response.choices[0].message.content.strip()
    content = _strip_json_fences(content)

    result = _parse_json_response(content)

    # Ensure required keys
    if "answer" not in result:
        # LLM may have returned the answer as a plain string or different key
        if isinstance(content, str) and not content.startswith("{"):
            result = {"answer": content, "caveats": ""}
        else:
            # Try to salvage: use the whole response as the answer
            result = {"answer": str(result), "caveats": ""}

    if "caveats" not in result:
        result["caveats"] = ""

    return {
        "answer": result.get("answer", "I was unable to generate a response. Please try again."),
        "caveats": result.get("caveats", ""),
    }
