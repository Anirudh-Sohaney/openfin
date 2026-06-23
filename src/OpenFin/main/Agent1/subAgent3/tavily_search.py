"""
tavily_search.py
Key objective: Interface with the Tavily Search API to perform deep internet
research for financial insights — supplier alternatives, market trends,
competitor pricing, industry benchmarks, and profit improvement opportunities.

Uses the official tavily-python SDK. Configure via environment variables:
    TAVILY_API_KEY  - Tavily API key (required)

Installation: pip install tavily-python
"""
import os
from typing import Dict, List, Optional, Any


def _get_tavily_client():
    """Get TavilyClient configured with API key."""
    try:
        from tavily import TavilyClient
    except ImportError:
        raise ImportError(
            "tavily-python package is required. Install with: pip install tavily-python"
        )

    api_key = os.environ.get(
        "TAVILY_API_KEY",
        "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",
    )

    return TavilyClient(api_key=api_key)


# ── Pre-defined research query templates ───────────

RESEARCH_QUERY_TEMPLATES = {
    "alternative_suppliers": (
        "alternative suppliers for {product_categories} wholesale bulk pricing "
        "better terms lower minimum order quantity"
    ),
    "lower_supplier_pricing": (
        "how to negotiate lower wholesale pricing from suppliers for "
        "{product_categories} cost reduction strategies"
    ),
    "better_supplier_terms": (
        "supplier payment terms negotiation net 60 net 90 extended terms "
        "for {product_categories} wholesale"
    ),
    "supplier_dependency_risks": (
        "supplier concentration risk mitigation diversify supply chain "
        "{product_categories} alternative vendors"
    ),
    "emerging_high_demand_products": (
        "trending high demand {product_categories} products {current_year} "
        "market growth forecast consumer electronics"
    ),
    "declining_product_categories": (
        "declining product categories {industry} market research "
        "{current_year} sunsetting products obsolescence risk"
    ),
    "seasonal_market_trends": (
        "seasonal sales trends {product_categories} {industry} "
        "quarterly demand patterns peak season forecast"
    ),
    "competitor_pricing_trends": (
        "competitor pricing trends {product_categories} {current_year} "
        "market price analysis competitive landscape"
    ),
    "industry_profit_margin_benchmarks": (
        "industry average profit margin benchmarks {industry} "
        "{current_year} small business comparison"
    ),
    "industry_expense_benchmarks": (
        "industry expense ratio benchmarks {industry} operating costs "
        "marketing spend shipping cost percentage of revenue"
    ),
    "inventory_optimization_opportunities": (
        "inventory management optimization strategies {industry} "
        "reduce carrying costs improve turnover just-in-time"
    ),
    "pricing_optimization_opportunities": (
        "pricing optimization strategies for {product_categories} "
        "dynamic pricing value-based pricing maximize margins"
    ),
    "customer_retention_opportunities": (
        "customer retention strategies {industry} small business "
        "loyalty programs reduce churn increase repeat purchases"
    ),
    "revenue_diversification_opportunities": (
        "revenue diversification strategies {industry} small business "
        "new income streams product line expansion"
    ),
    "cost_reduction_opportunities": (
        "cost reduction strategies {industry} small business "
        "operational efficiency lower expenses procurement savings"
    ),
    "automation_opportunities": (
        "business process automation {industry} small business "
        "software tools AI workflow automation reduce labor costs"
    ),
    "operational_efficiency_improvements": (
        "operational efficiency improvements {industry} retail "
        "lean operations process optimization reduce waste"
    ),
    "cash_flow_optimization_strategies": (
        "cash flow optimization strategies {industry} small business "
        "working capital management improve liquidity"
    ),
    "new_sales_channel_opportunities": (
        "new sales channel opportunities {product_categories} {current_year} "
        "online marketplace DTC ecommerce expansion"
    ),
    "geographic_expansion_opportunities": (
        "geographic expansion opportunities {product_categories} "
        "regional market analysis underserved markets growth regions"
    ),
}


def build_search_queries(
    research_topics: List[str],
    product_categories: str = "consumer electronics",
    industry: str = "consumer electronics retail",
    current_year: str = "2025",
    topic_contexts: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Build Tavily search queries for a list of research topics.

    Args:
        research_topics: List of topic identifiers from RESEARCH_QUERY_TEMPLATES.
        product_categories: Product category description (e.g., "wireless headphones, monitors").
        industry: Industry name for benchmark queries.
        current_year: Current year for time-sensitive searches.
        topic_contexts: Optional dict mapping topic → context_for_search from LLM.

    Returns:
        Dict mapping topic → search query string.
    """
    queries = {}
    topic_contexts = topic_contexts or {}
    for topic in research_topics:
        template = RESEARCH_QUERY_TEMPLATES.get(topic)
        if template:
            query = template.format(
                product_categories=product_categories,
                industry=industry,
                current_year=current_year,
            )
            # Append LLM-identified context to make search more specific
            extra = topic_contexts.get(topic, "")
            if extra:
                query = f"{query} {extra}"
            queries[topic] = query
        else:
            queries[topic] = (
                f"{topic.replace('_', ' ')} {product_categories} "
                f"{industry} {current_year} profit improvement"
            )
    return queries


def search_topic(query: str, max_results: int = 5) -> Optional[Dict[str, Any]]:
    """
    Perform a single Tavily search and return the structured results.

    Uses advanced search depth for deep research.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        Dict with keys: answer (AI summary), results (list of {url, content}),
        or None on failure.
    """
    try:
        client = _get_tavily_client()
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
        )
        return {
            "query": query,
            "answer": response.get("answer", ""),
            "results": response.get("results", []),
        }
    except Exception as e:
        print(f"  Tavily search failed for query '{query[:80]}...': {e}")
        return None


def search_topics(
    queries: Dict[str, str],
    max_results_per_topic: int = 5,
) -> Dict[str, Dict[str, Any]]:
    """
    Perform Tavily searches for multiple topics.

    Args:
        queries: Dict mapping topic → search query string.
        max_results_per_topic: Max results per search.

    Returns:
        Dict mapping topic → search result dict (or None for failed searches).
    """
    results = {}
    for topic, query in queries.items():
        print(f"  Searching: {topic} ...")
        result = search_topic(query, max_results=max_results_per_topic)
        results[topic] = result
    return results



