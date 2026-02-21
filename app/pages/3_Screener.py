"""Stock Screener page — filter NASDAQ 100 by financial metrics."""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
from backend.data.financial import get_metrics
from backend.data.cache import add_to_watchlist, get_watchlist
from config.tickers import NASDAQ_100

st.set_page_config(page_title="Screener — DualLens", page_icon="🔍", layout="wide")

st.title("🔍 Stock Screener")
st.markdown("Filter and sort NASDAQ 100 stocks by fundamental metrics.")
st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
with st.expander("⚙️ Filter Settings", expanded=True):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        pe_max = st.slider("Max P/E Ratio", 0, 200, 60, step=5)
        pe_min = st.slider("Min P/E Ratio", 0, 100, 5, step=1)
    with fc2:
        mktcap_min = st.slider("Min Market Cap ($B)", 0, 500, 10, step=10)
        beta_max = st.slider("Max Beta", 0.0, 4.0, 2.5, step=0.1)
    with fc3:
        div_min = st.slider("Min Dividend Yield (%)", 0.0, 10.0, 0.0, step=0.1)
        margin_min = st.slider("Min Profit Margin (%)", -50, 50, 0, step=5)

run_screen = st.button("🔍 Run Screen", type="primary")
st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Fetching NASDAQ 100 data…")
def load_nasdaq_data():
    rows = []
    for symbol in NASDAQ_100:
        m = get_metrics(symbol)
        if "error" not in m:
            rows.append(m)
    return rows


if run_screen or "screener_df" in st.session_state:
    if run_screen or "screener_raw" not in st.session_state:
        with st.spinner("Loading NASDAQ 100 data…"):
            st.session_state.screener_raw = load_nasdaq_data()

    raw = st.session_state.screener_raw
    if not raw:
        st.error("Could not load market data. Check your internet connection.")
        st.stop()

    df = pd.DataFrame(raw)

    # Apply filters
    mask = (
        (df["pe_ratio"] >= pe_min) &
        (df["pe_ratio"] <= pe_max) &
        (df["market_cap"] >= mktcap_min) &
        (df["beta"] <= beta_max) &
        (df["dividend_yield"] >= div_min) &
        (df["profit_margin"] >= margin_min)
    )
    filtered = df[mask].copy()

    st.markdown(f"**{len(filtered)} stocks** match your filters (from {len(df)} screened)")

    if filtered.empty:
        st.warning("No stocks match the current filters. Try relaxing your criteria.")
    else:
        # Sort control
        sort_col = st.selectbox(
            "Sort by",
            ["market_cap", "pe_ratio", "revenue", "profit_margin", "beta", "dividend_yield"],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        sort_asc = st.checkbox("Ascending", value=False)
        filtered = filtered.sort_values(sort_col, ascending=sort_asc).reset_index(drop=True)

        # Display columns
        display_cols = ["symbol", "name", "price", "market_cap", "pe_ratio",
                        "revenue", "profit_margin", "beta", "dividend_yield", "sector"]
        display_df = filtered[display_cols].rename(columns={
            "symbol": "Ticker",
            "name": "Company",
            "price": "Price ($)",
            "market_cap": "Mkt Cap ($B)",
            "pe_ratio": "P/E",
            "revenue": "Revenue ($B)",
            "profit_margin": "Margin (%)",
            "beta": "Beta",
            "dividend_yield": "Div Yield (%)",
            "sector": "Sector",
        })

        # Render table
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Price ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Mkt Cap ($B)": st.column_config.NumberColumn(format="$%.1fB"),
                "P/E": st.column_config.NumberColumn(format="%.1f"),
                "Revenue ($B)": st.column_config.NumberColumn(format="$%.1fB"),
                "Margin (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Div Yield (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

        # Add to watchlist
        st.divider()
        st.subheader("Add to Watchlist")
        watchlist = get_watchlist()
        available = [s for s in filtered["symbol"].tolist() if s not in watchlist]

        if available:
            to_add = st.multiselect("Select tickers to add", options=available)
            if st.button("➕ Add selected to watchlist") and to_add:
                for s in to_add:
                    add_to_watchlist(s)
                st.success(f"Added {', '.join(to_add)} to your watchlist.")
                st.rerun()
        else:
            st.info("All filtered tickers are already in your watchlist.")
else:
    st.info('Set your filters above and click **"Run Screen"** to find matching stocks.')
    st.markdown(
        """
        **Available filters:**
        - **P/E Ratio** — Valuation filter (lower = cheaper relative to earnings)
        - **Market Cap** — Company size filter
        - **Beta** — Volatility filter (1.0 = market average, >1 = more volatile)
        - **Dividend Yield** — Income filter
        - **Profit Margin** — Profitability filter
        """
    )
