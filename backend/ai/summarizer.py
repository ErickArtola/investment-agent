"""AI summarization functions using Ollama (phi3:mini)."""
from backend.ai.llm import llm


def summarize_stock(symbol: str, metrics: dict, news_items: list[dict]) -> str:
    """
    Generate a 3-4 sentence investment summary for a stock.
    Combines financial metrics + recent news headlines.
    """
    news_text = ""
    if news_items:
        headlines = [f"- {a['title']}" for a in news_items[:5]]
        news_text = "Recent news:\n" + "\n".join(headlines)

    prompt = f"""You are a concise financial analyst. Write a 3-4 sentence summary
of {symbol} ({metrics.get('name', symbol)}) for an investor.

Financial snapshot:
- Price: ${metrics.get('price', 'N/A')}
- Market Cap: ${metrics.get('market_cap', 'N/A')}B
- P/E Ratio: {metrics.get('pe_ratio', 'N/A')}
- Revenue: ${metrics.get('revenue', 'N/A')}B
- Beta: {metrics.get('beta', 'N/A')}
- Dividend Yield: {metrics.get('dividend_yield', 'N/A')}%
- Profit Margin: {metrics.get('profit_margin', 'N/A')}%
- Sector: {metrics.get('sector', 'N/A')}

{news_text}

Write a factual, neutral summary. Focus on key investment considerations."""

    try:
        return llm.invoke(prompt).strip()
    except Exception as e:
        return f"Summary unavailable: {e}"


def summarize_news(news_items: list[dict]) -> str:
    """
    Generate a one-paragraph digest of multiple news headlines.
    """
    if not news_items:
        return "No recent news available."

    headlines = "\n".join([f"- {a['title']}: {a.get('summary', '')}" for a in news_items[:6]])

    prompt = f"""Summarize the following financial news headlines in 2-3 sentences.
Focus on the key themes and their potential market impact.

Headlines:
{headlines}

Summary:"""

    try:
        return llm.invoke(prompt).strip()
    except Exception as e:
        return f"News digest unavailable: {e}"


def summarize_sec_filings(symbol: str, filings: list[dict]) -> str:
    """
    Generate a bullet-point summary of key points from recent SEC filings.
    """
    if not filings:
        return f"No SEC filings found for {symbol}."

    filings_text = "\n".join([
        f"- {f['form']} ({f['date']}): {f['description']}"
        for f in filings
    ])

    prompt = f"""Based on the following recent SEC filings for {symbol}, provide 3-4 bullet points
summarizing what an investor should know. Focus on risk factors, revenue trends, and strategic updates.

Filings:
{filings_text}

Key investor takeaways (bullet points):"""

    try:
        return llm.invoke(prompt).strip()
    except Exception as e:
        return f"SEC summary unavailable: {e}"
