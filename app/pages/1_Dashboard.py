"""Dashboard page — per-stock deep-dive."""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import plotly.graph_objects as go
from backend.data.financial import get_metrics, get_history, get_price_change
from backend.data.scraper import get_news
from backend.data.sec_client import get_recent_filings
from backend.data.cache import (
    load_metrics, save_metrics, load_news, save_news, get_watchlist
)
from backend.ai.summarizer import summarize_stock, summarize_news, summarize_sec_filings
from backend.ai.scorer import score_stock
from backend.scheduler import refresh_ticker_now
from config.settings import SCORE_STRONG_BUY, SCORE_BUY, SCORE_HOLD

st.set_page_config(page_title="Dashboard — DualLens", page_icon="📊", layout="wide")

# ── Helpers ──────────────────────────────────────────────────────────────────

def rec_badge(rec: str) -> str:
    colors = {
        "STRONG BUY": "🟢",
        "BUY": "🟩",
        "HOLD": "🟡",
        "SELL": "🔴",
    }
    return f"{colors.get(rec, '⚪')} **{rec}**"


def price_delta_color(pct: float) -> str:
    return "normal" if pct >= 0 else "inverse"


def build_chart(symbol: str, period: str) -> go.Figure:
    df = get_history(symbol, period)
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name=symbol,
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ))
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10),
        height=380,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── Ticker selector ───────────────────────────────────────────────────────────
st.title("📊 Stock Dashboard")

watchlist = get_watchlist()
if not watchlist:
    st.warning("Your watchlist is empty. Add tickers in the sidebar on the Home page.")
    st.stop()

selected = st.selectbox("Select a stock", options=watchlist)

col_refresh, _ = st.columns([1, 6])
with col_refresh:
    if st.button("🔄 Refresh data"):
        refresh_ticker_now(selected)
        # Clear cached keys so fresh data loads
        for key in [f"metrics_{selected}", f"news_{selected}", f"score_{selected}"]:
            st.session_state.pop(key, None)
        st.toast(f"Refreshing {selected}…")

st.divider()

# ── Load / cache metrics ──────────────────────────────────────────────────────
cache_key = f"metrics_{selected}"
if cache_key not in st.session_state:
    metrics = load_metrics(selected)
    if not metrics:
        with st.spinner(f"Fetching {selected} data…"):
            metrics = get_metrics(selected)
            save_metrics(selected, metrics)
    st.session_state[cache_key] = metrics

metrics = st.session_state[cache_key]

# ── Header row ────────────────────────────────────────────────────────────────
price, pct = get_price_change(selected)
name = metrics.get("name", selected)

hcol1, hcol2, hcol3, hcol4 = st.columns([3, 1.5, 1.5, 1.5])
with hcol1:
    st.subheader(f"{selected} — {name}")
with hcol2:
    st.metric("Price", f"${price}", f"{pct:+.2f}%", delta_color=price_delta_color(pct))
with hcol3:
    st.metric("Market Cap", f"${metrics.get('market_cap', 0)}B")
with hcol4:
    score_data = st.session_state.get(f"score_{selected}")
    if score_data:
        st.metric("AI Score", f"{score_data.get('overall', '—')}/10")
        st.markdown(rec_badge(score_data.get("recommendation", "—")))

st.divider()

# ── Chart + Metrics columns ───────────────────────────────────────────────────
chart_col, metrics_col = st.columns([2.5, 1])

with chart_col:
    period = st.radio(
        "Period", ["1mo", "3mo", "6mo", "1y", "3y"],
        horizontal=True, index=3, key="chart_period"
    )
    st.plotly_chart(build_chart(selected, period), use_container_width=True)

with metrics_col:
    st.subheader("Key Metrics")
    rows = [
        ("P/E Ratio", metrics.get("pe_ratio", "N/A")),
        ("Forward P/E", metrics.get("forward_pe", "N/A")),
        ("Revenue", f"${metrics.get('revenue', 0)}B"),
        ("Profit Margin", f"{metrics.get('profit_margin', 0)}%"),
        ("Beta", metrics.get("beta", "N/A")),
        ("Dividend Yield", f"{metrics.get('dividend_yield', 0)}%"),
        ("52W High", f"${metrics.get('52w_high', 'N/A')}"),
        ("52W Low", f"${metrics.get('52w_low', 'N/A')}"),
        ("Sector", metrics.get("sector", "N/A")),
    ]
    for label, value in rows:
        c1, c2 = st.columns(2)
        c1.markdown(f"**{label}**")
        c2.markdown(str(value))

st.divider()

# ── AI Summary ────────────────────────────────────────────────────────────────
st.subheader("🤖 AI Investment Summary")

sum_key = f"summary_{selected}"
if sum_key not in st.session_state:
    news_cache = load_news(selected) or []
    with st.spinner("Generating AI summary…"):
        st.session_state[sum_key] = summarize_stock(selected, metrics, news_cache)

st.write(st.session_state[sum_key])

# ── Investment Score ──────────────────────────────────────────────────────────
st.subheader("📐 Investment Score")

score_key = f"score_{selected}"
if score_key not in st.session_state:
    with st.spinner("Scoring investment…"):
        st.session_state[score_key] = score_stock(selected, metrics)

score = st.session_state[score_key]
s1, s2, s3, s4 = st.columns(4)
s1.metric("Quantitative", f"{score.get('quantitative', '—')}/10")
s2.metric("Qualitative", f"{score.get('qualitative', '—')}/10")
s3.metric("Overall", f"{score.get('overall', '—')}/10")
with s4:
    st.markdown("**Recommendation**")
    st.markdown(rec_badge(score.get("recommendation", "—")))

st.info(f"**Justification:** {score.get('justification', 'N/A')}")

st.divider()

# ── News Feed ─────────────────────────────────────────────────────────────────
st.subheader("📰 Latest News")

news_key = f"news_{selected}"
if news_key not in st.session_state:
    articles = load_news(selected)
    if not articles:
        with st.spinner("Fetching news…"):
            articles = get_news(selected)
            if articles:
                save_news(selected, articles)
    st.session_state[news_key] = articles or []

articles = st.session_state[news_key]

if articles:
    digest_key = f"news_digest_{selected}"
    if digest_key not in st.session_state:
        with st.spinner("Summarizing news…"):
            st.session_state[digest_key] = summarize_news(articles)
    st.write(st.session_state[digest_key])

    st.markdown("**Headlines:**")
    for article in articles:
        source = article.get("source", "")
        date = article.get("date", "")
        url = article.get("url", "#")
        title = article.get("title", "")
        st.markdown(f"- [{title}]({url}) `{source}` — {date}")
else:
    st.info("No news found. Try refreshing.")

st.divider()

# ── SEC Filings ───────────────────────────────────────────────────────────────
st.subheader("🏛️ SEC Filings")

sec_key = f"sec_{selected}"
if sec_key not in st.session_state:
    with st.spinner("Fetching SEC filings…"):
        st.session_state[sec_key] = get_recent_filings(selected)

filings = st.session_state[sec_key]

if filings:
    sec_sum_key = f"sec_summary_{selected}"
    if sec_sum_key not in st.session_state:
        with st.spinner("Summarizing filings…"):
            st.session_state[sec_sum_key] = summarize_sec_filings(selected, filings)
    st.write(st.session_state[sec_sum_key])

    for filing in filings:
        badge = {"10-K": "📋", "10-Q": "📄", "8-K": "⚡"}.get(filing["form"], "📁")
        st.markdown(
            f"{badge} **{filing['form']}** — {filing['date']} "
            f"[View on EDGAR]({filing['url']})"
        )
else:
    st.info("No SEC filings found for this ticker.")
