"""DualLens Analytics — Streamlit entry point."""
import sys
from pathlib import Path

# Make project root importable
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from backend.scheduler import start_scheduler
from backend.data.cache import get_watchlist, add_to_watchlist, remove_from_watchlist
from backend.ai.llm import is_ollama_running
from config.tickers import SEED_TICKERS, NASDAQ_100

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DualLens Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Start background scheduler once ─────────────────────────────────────────
if "scheduler_started" not in st.session_state:
    start_scheduler()
    st.session_state.scheduler_started = True

# ── Ollama health check ──────────────────────────────────────────────────────
if "ollama_checked" not in st.session_state:
    st.session_state.ollama_ok = is_ollama_running()
    st.session_state.ollama_checked = True

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 DualLens Analytics")
    st.caption("AI-powered investment intelligence")

    if not st.session_state.ollama_ok:
        st.error("⚠️ Ollama not running.\nStart it with: `ollama serve`")
    else:
        st.success("✅ AI engine online (phi3:mini)")

    st.divider()

    # Watchlist management
    st.subheader("My Watchlist")
    watchlist = get_watchlist()

    # Add ticker
    all_tickers = sorted(set(NASDAQ_100 + SEED_TICKERS))
    new_ticker = st.selectbox(
        "Add a ticker",
        options=[""] + [t for t in all_tickers if t not in watchlist],
        format_func=lambda x: "— select —" if x == "" else x,
    )
    if new_ticker:
        add_to_watchlist(new_ticker)
        st.rerun()

    # Display watchlist with remove buttons
    watchlist = get_watchlist()
    for symbol in watchlist:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**{symbol}**")
        with col2:
            if st.button("✕", key=f"rm_{symbol}", help=f"Remove {symbol}"):
                remove_from_watchlist(symbol)
                st.rerun()

    st.divider()
    st.caption("Data refreshes at 9 AM & 3 PM daily")

# ── Home page content ────────────────────────────────────────────────────────
st.title("Welcome to DualLens Analytics")
st.markdown(
    """
    **DualLens Analytics** combines real-time financial data with AI-powered qualitative
    analysis to help you make smarter investment decisions — all running locally on your Mac.

    ### Get started
    - **Dashboard** — Deep-dive into any stock: price charts, metrics, AI summary, news & SEC filings
    - **Suggestions** — AI-ranked top picks from the NASDAQ 100 screened daily
    - **Screener** — Filter stocks by P/E, market cap, beta, and more

    Use the **sidebar** to manage your watchlist, then navigate using the pages above.
    """
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Watchlist Size", len(watchlist))
with col2:
    st.metric("Universe", "NASDAQ 100")
with col3:
    st.metric("AI Model", "phi3:mini (local)")
