"""AI Suggestions page — top picks from NASDAQ 100."""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from datetime import datetime
from backend.data.financial import get_metrics
from backend.data.cache import load_all_scores, load_score
from backend.ai.scorer import score_stock, score_batch
from config.tickers import NASDAQ_100, SEED_TICKERS

st.set_page_config(page_title="Suggestions — DualLens", page_icon="💡", layout="wide")

# ── Helpers ──────────────────────────────────────────────────────────────────

REC_COLORS = {
    "STRONG BUY": "#26a69a",
    "BUY": "#66bb6a",
    "HOLD": "#ffa726",
    "SELL": "#ef5350",
}

REC_ICONS = {
    "STRONG BUY": "🟢",
    "BUY": "🟩",
    "HOLD": "🟡",
    "SELL": "🔴",
}


def render_suggestion_card(item: dict, rank: int):
    rec = item.get("recommendation", "HOLD")
    icon = REC_ICONS.get(rec, "⚪")
    color = REC_COLORS.get(rec, "#888")

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([0.5, 2, 1.5, 3])
        with c1:
            st.markdown(f"### #{rank}")
        with c2:
            st.markdown(f"### {item.get('symbol', '')}")
            st.caption(item.get("name", ""))
        with c3:
            st.metric("Overall Score", f"{item.get('overall', 0)}/10")
            st.markdown(f"{icon} **{rec}**")
        with c4:
            st.markdown(f"**Quant:** {item.get('quantitative', 0)}/10 &nbsp;|&nbsp; **Qual:** {item.get('qualitative', 0)}/10")
            st.write(item.get("justification", "")[:300])
            if item.get("updated_at"):
                st.caption(f"Last scored: {item.get('updated_at')}")


# ── Page ──────────────────────────────────────────────────────────────────────
st.title("💡 AI Stock Suggestions")
st.markdown(
    "Daily AI-ranked top picks from the NASDAQ 100, scored on both financial strength "
    "and AI strategy quality."
)
st.divider()

# Options
col_opt1, col_opt2, col_opt3 = st.columns([1, 1, 2])
with col_opt1:
    top_n = st.number_input("Top N picks", min_value=3, max_value=20, value=5)
with col_opt2:
    universe = st.selectbox("Screen from", ["NASDAQ 100", "My Watchlist"])
with col_opt3:
    force_rescore = st.checkbox("Force re-score (ignores cache)", value=False)

run = st.button("🚀 Generate Suggestions", type="primary")

st.divider()

# ── Load or generate ──────────────────────────────────────────────────────────
cache_key = f"suggestions_{universe}_{top_n}"

if run or cache_key not in st.session_state or force_rescore:
    from config.tickers import SEED_TICKERS
    from backend.data.cache import get_watchlist

    if universe == "My Watchlist":
        tickers_to_screen = get_watchlist() or SEED_TICKERS
    else:
        tickers_to_screen = NASDAQ_100

    st.info(f"Screening {len(tickers_to_screen)} tickers… This may take a few minutes on first run.")
    progress = st.progress(0, text="Fetching financial data…")

    metrics_map = {}
    for i, symbol in enumerate(tickers_to_screen):
        m = get_metrics(symbol)
        if "error" not in m and m.get("pe_ratio", 0) > 0:
            metrics_map[symbol] = m
        progress.progress((i + 1) / len(tickers_to_screen), text=f"Fetching {symbol}…")

    progress.progress(1.0, text="Scoring top candidates…")

    # Pre-filter to best candidates by market cap before expensive AI scoring
    import pandas as pd
    if metrics_map:
        df = pd.DataFrame(metrics_map.values()).set_index("symbol")
        top_candidates = (
            df[df["pe_ratio"] > 0]
            .sort_values("market_cap", ascending=False)
            .head(min(30, len(metrics_map)))
            .index.tolist()
        )
    else:
        top_candidates = list(metrics_map.keys())[:30]

    filtered_metrics = {s: metrics_map[s] for s in top_candidates if s in metrics_map}

    with st.spinner("AI scoring candidates…"):
        results = score_batch(top_candidates, filtered_metrics, top_n=top_n)

    st.session_state[cache_key] = {
        "results": results,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    progress.empty()

data = st.session_state.get(cache_key)

if data and data.get("results"):
    st.markdown(f"**Generated at:** {data.get('generated_at', '—')}")
    st.markdown(f"### Top {len(data['results'])} Picks")

    for rank, item in enumerate(data["results"], 1):
        render_suggestion_card(item, rank)
else:
    st.info('Click **"Generate Suggestions"** to run the AI screener.')
    st.markdown(
        """
        **How it works:**
        1. Fetches live financial metrics for NASDAQ 100 tickers
        2. Pre-filters by market cap to select top candidates
        3. Scores each candidate using the DualLens dual-lens framework:
           - **40% Quantitative**: P/E ratio, revenue, beta, profit margin
           - **60% Qualitative**: AI strategy analysis via local RAG pipeline
        4. Returns top N ranked picks with justification
        """
    )
