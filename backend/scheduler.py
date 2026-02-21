"""Background scheduler — refreshes data at 9 AM and 3 PM daily."""
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.data.financial import get_metrics
from backend.data.scraper import get_news
from backend.data.sec_client import get_recent_filings
from backend.data.cache import (
    save_metrics, save_news, get_watchlist,
    add_to_watchlist, init_db,
)
from config.settings import REFRESH_HOURS
from config.tickers import SEED_TICKERS

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def _refresh_ticker(symbol: str):
    """Fetch and cache metrics + news for a single ticker."""
    try:
        metrics = get_metrics(symbol)
        if "error" not in metrics:
            save_metrics(symbol, metrics)

        news = get_news(symbol)
        if news:
            save_news(symbol, news)
    except Exception:
        pass


def _refresh_all():
    """Refresh all tickers currently in the watchlist."""
    tickers = get_watchlist()
    for symbol in tickers:
        _refresh_ticker(symbol)


def _seed_watchlist():
    """Ensure seed tickers are in the watchlist on first run."""
    for symbol in SEED_TICKERS:
        add_to_watchlist(symbol)


def start_scheduler():
    """
    Initialize the DB, seed the watchlist, and start the background scheduler.
    Safe to call multiple times — only starts once.
    """
    global _scheduler
    with _lock:
        if _scheduler is not None:
            return

        init_db()
        _seed_watchlist()

        _scheduler = BackgroundScheduler(daemon=True)

        for hour in REFRESH_HOURS:
            _scheduler.add_job(
                _refresh_all,
                trigger=CronTrigger(hour=hour, minute=0),
                id=f"refresh_{hour}",
                replace_existing=True,
            )

        _scheduler.start()

        # Run an immediate refresh in a background thread so the UI doesn't block
        threading.Thread(target=_refresh_all, daemon=True).start()


def refresh_ticker_now(symbol: str):
    """Force-refresh a single ticker immediately (called from UI)."""
    threading.Thread(target=_refresh_ticker, args=(symbol,), daemon=True).start()


def stop_scheduler():
    global _scheduler
    with _lock:
        if _scheduler:
            _scheduler.shutdown(wait=False)
            _scheduler = None
