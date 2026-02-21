"""Investment scoring engine — refactored from notebook DualLens scoring logic."""
from backend.ai.llm import llm
from backend.ai.rag import rag_query
from backend.data.cache import save_score, load_score
from config.settings import SCORE_STRONG_BUY, SCORE_BUY, SCORE_HOLD
import re


def _recommendation_label(score: float) -> str:
    if score >= SCORE_STRONG_BUY:
        return "STRONG BUY"
    elif score >= SCORE_BUY:
        return "BUY"
    elif score >= SCORE_HOLD:
        return "HOLD"
    else:
        return "SELL"


def _extract_score(text: str, label: str) -> float:
    """Parse a numeric score from LLM output."""
    pattern = rf"{label}[^\d]*(\d+(?:\.\d+)?)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return min(10.0, max(0.0, float(match.group(1))))
    # Fallback: find any number 0-10 in the line containing the label
    lines = [l for l in text.split("\n") if label.lower() in l.lower()]
    if lines:
        nums = re.findall(r"\d+(?:\.\d+)?", lines[0])
        if nums:
            return min(10.0, max(0.0, float(nums[0])))
    return 5.0


def score_stock(symbol: str, metrics: dict, force: bool = False) -> dict:
    """
    Score a stock using dual-source analysis (quantitative + qualitative).
    Returns dict with keys: quantitative, qualitative, overall, recommendation, justification.
    Caches result in SQLite.
    """
    # Return cached score if available and not forced
    if not force:
        cached = load_score(symbol)
        if cached:
            return cached

    # Qualitative context from RAG
    ai_context = rag_query(
        f"What are the key AI initiatives, strategic projects, and competitive advantages of {symbol}? "
        f"What risks or challenges does the company face in its AI strategy?"
    )

    metrics_str = f"""
Symbol: {symbol} | Name: {metrics.get('name', symbol)}
Market Cap: ${metrics.get('market_cap', 0)}B | P/E Ratio: {metrics.get('pe_ratio', 0)}
Revenue: ${metrics.get('revenue', 0)}B | Beta: {metrics.get('beta', 0)}
Dividend Yield: {metrics.get('dividend_yield', 0)}% | Profit Margin: {metrics.get('profit_margin', 0)}%
52W High: ${metrics.get('52w_high', 0)} | 52W Low: ${metrics.get('52w_low', 0)}
"""

    prompt = f"""You are DualLens Analytics, a dual-lens investment analyst.
Evaluate {symbol} using quantitative (financial) and qualitative (AI strategy) analysis.

=== FINANCIAL DATA ===
{metrics_str}

=== AI STRATEGY CONTEXT (from company documents) ===
{ai_context}

=== SCORING FRAMEWORK ===
Quantitative Score (0-10): Based on valuation (P/E), growth (revenue), risk (beta), and profitability (margin).
Qualitative Score (0-10): Based on AI initiative strength, innovation leadership, and strategic positioning.
Overall Score: 60% qualitative + 40% quantitative.

=== OUTPUT FORMAT (use exactly these labels) ===
Quantitative Score: X.X/10
Qualitative Score: X.X/10
Overall Score: X.X/10
Recommendation: [STRONG BUY / BUY / HOLD / SELL]
Justification: [2-3 sentences explaining the recommendation]
Key Risks: [1-2 sentences on main risks]"""

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        response = f"Quantitative Score: 5.0/10\nQualitative Score: 5.0/10\nOverall Score: 5.0/10\nRecommendation: HOLD\nJustification: LLM error: {e}\nKey Risks: N/A"

    quant = _extract_score(response, "Quantitative Score")
    qual = _extract_score(response, "Qualitative Score")
    overall = _extract_score(response, "Overall Score")

    # Recompute overall if parsing failed
    if overall == 5.0 and (quant != 5.0 or qual != 5.0):
        overall = round(0.4 * quant + 0.6 * qual, 2)

    recommendation = _recommendation_label(overall)

    # Extract justification
    justification = ""
    for line in response.split("\n"):
        if "justification" in line.lower():
            justification = line.split(":", 1)[-1].strip()
            break
    if not justification:
        justification = response[:300]

    result = {
        "quantitative": round(quant, 1),
        "qualitative": round(qual, 1),
        "overall": round(overall, 1),
        "recommendation": recommendation,
        "justification": justification,
    }

    save_score(symbol, quant, qual, overall, recommendation, justification)
    return result


def score_batch(tickers: list[str], metrics_map: dict, top_n: int = 5) -> list[dict]:
    """
    Score multiple tickers and return the top N by overall score.
    metrics_map: {symbol: metrics_dict}
    """
    results = []
    for symbol in tickers:
        if symbol not in metrics_map:
            continue
        score = score_stock(symbol, metrics_map[symbol])
        score["symbol"] = symbol
        score["name"] = metrics_map[symbol].get("name", symbol)
        results.append(score)

    results.sort(key=lambda x: x.get("overall", 0), reverse=True)
    return results[:top_n]
