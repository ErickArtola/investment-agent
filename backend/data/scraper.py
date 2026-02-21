"""News scraping from Yahoo Finance and Reuters."""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from config.settings import REQUEST_TIMEOUT, USER_AGENT, NEWS_MAX_ARTICLES


HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch_html(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def scrape_yahoo_finance_news(symbol: str) -> list[dict]:
    """Scrape latest news headlines for a ticker from Yahoo Finance."""
    url = f"https://finance.yahoo.com/quote/{symbol}/news/"
    soup = _fetch_html(url)
    if not soup:
        return []

    articles = []
    # Yahoo Finance news items
    for item in soup.select("li.stream-item, div[data-testid='storyitem']")[:NEWS_MAX_ARTICLES]:
        title_tag = item.select_one("h3, h2, a[data-ylk]")
        link_tag = item.select_one("a[href]")
        summary_tag = item.select_one("p")

        title = title_tag.get_text(strip=True) if title_tag else ""
        href = link_tag.get("href", "") if link_tag else ""
        summary = summary_tag.get_text(strip=True) if summary_tag else ""

        if not title:
            continue

        # Normalize relative links
        if href.startswith("/"):
            href = f"https://finance.yahoo.com{href}"

        articles.append({
            "title": title,
            "url": href,
            "summary": summary[:200],
            "source": "Yahoo Finance",
            "date": datetime.now().strftime("%Y-%m-%d"),
        })

    return articles


def scrape_reuters_news(symbol: str) -> list[dict]:
    """Scrape Reuters search results for a ticker symbol."""
    url = f"https://www.reuters.com/search/news?blob={symbol}&sortBy=date&dateRange=pastWeek"
    soup = _fetch_html(url)
    if not soup:
        return []

    articles = []
    for item in soup.select("div.search-result-content, article.story-content")[:NEWS_MAX_ARTICLES // 2]:
        title_tag = item.select_one("h3.story-title, h3, h2")
        link_tag = item.select_one("a[href]")
        summary_tag = item.select_one("p.story-content, p")

        title = title_tag.get_text(strip=True) if title_tag else ""
        href = link_tag.get("href", "") if link_tag else ""
        summary = summary_tag.get_text(strip=True) if summary_tag else ""

        if not title:
            continue

        if href.startswith("/"):
            href = f"https://www.reuters.com{href}"

        articles.append({
            "title": title,
            "url": href,
            "summary": summary[:200],
            "source": "Reuters",
            "date": datetime.now().strftime("%Y-%m-%d"),
        })

    return articles


def get_news(symbol: str) -> list[dict]:
    """Aggregate news from all sources for a ticker, deduplicated by title."""
    yahoo = scrape_yahoo_finance_news(symbol)
    reuters = scrape_reuters_news(symbol)

    combined = yahoo + reuters
    seen = set()
    unique = []
    for article in combined:
        if article["title"] not in seen:
            seen.add(article["title"])
            unique.append(article)

    return unique[:NEWS_MAX_ARTICLES]
