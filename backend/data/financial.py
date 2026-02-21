"""Financial data fetching via yfinance."""
import yfinance as yf
import pandas as pd
from typing import Optional


def get_metrics(symbol: str) -> dict:
    """
    Fetch key financial metrics for a ticker.
    Returns a dict with normalized values (Market Cap in billions, etc.)
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        market_cap = info.get("marketCap", 0) or 0
        revenue = info.get("totalRevenue", 0) or 0
        dividend = info.get("dividendYield", 0) or 0

        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "sector": info.get("sector", "N/A"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
            "prev_close": info.get("previousClose", 0),
            "market_cap": round(market_cap / 1e9, 2),       # billions
            "pe_ratio": round(info.get("trailingPE", 0) or 0, 2),
            "forward_pe": round(info.get("forwardPE", 0) or 0, 2),
            "dividend_yield": round(dividend * 100, 2),      # percent
            "beta": round(info.get("beta", 0) or 0, 2),
            "revenue": round(revenue / 1e9, 2),              # billions
            "profit_margin": round((info.get("profitMargins", 0) or 0) * 100, 2),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "avg_volume": info.get("averageVolume", 0),
        }
    except Exception as e:
        return {"symbol": symbol, "name": symbol, "error": str(e)}


def get_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch OHLCV historical price data.
    period options: 1mo, 3mo, 6mo, 1y, 3y
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        df.index = pd.to_datetime(df.index)
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return pd.DataFrame()


def get_price_change(symbol: str) -> tuple[float, float]:
    """Return (current_price, pct_change_from_prev_close)."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        prev = info.get("previousClose", price)
        pct = ((price - prev) / prev * 100) if prev else 0
        return round(price, 2), round(pct, 2)
    except Exception:
        return 0.0, 0.0


def screen_nasdaq(tickers: list[str], max_pe: float = 50, min_market_cap: float = 10) -> pd.DataFrame:
    """
    Batch-fetch metrics for a list of tickers and filter by basic criteria.
    Returns a DataFrame sorted by market cap descending.
    """
    rows = []
    for symbol in tickers:
        m = get_metrics(symbol)
        if "error" not in m:
            rows.append(m)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Basic quality filter
    df = df[(df["pe_ratio"] > 0) & (df["pe_ratio"] <= max_pe) & (df["market_cap"] >= min_market_cap)]
    return df.sort_values("market_cap", ascending=False).reset_index(drop=True)
