"""SEC EDGAR API client — no API key required."""
import requests
from config.settings import REQUEST_TIMEOUT

BASE_URL = "https://data.sec.gov"
HEADERS = {"User-Agent": "DualLens Analytics contact@duallens.local"}

# Cache CIK lookups in memory
_cik_cache: dict[str, str] = {}


def _get_cik(symbol: str) -> str | None:
    """Map a ticker symbol to its SEC CIK number."""
    if symbol in _cik_cache:
        return _cik_cache[symbol]
    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == symbol.upper():
                cik = str(entry["cik_str"]).zfill(10)
                _cik_cache[symbol] = cik
                return cik
    except Exception:
        pass
    return None


def get_recent_filings(symbol: str, form_types: list[str] = None) -> list[dict]:
    """
    Fetch the most recent SEC filings for a ticker.
    form_types: list of form types to filter, e.g. ["10-K", "10-Q", "8-K"]
    Returns list of filing dicts with keys: form, date, description, url
    """
    if form_types is None:
        form_types = ["10-K", "10-Q", "8-K"]

    cik = _get_cik(symbol)
    if not cik:
        return []

    try:
        url = f"{BASE_URL}/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        descriptions = filings.get("primaryDocument", [])
        accession_numbers = filings.get("accessionNumber", [])

        results = []
        for form, date, desc, acc in zip(forms, dates, descriptions, accession_numbers):
            if form in form_types:
                acc_clean = acc.replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/full-index/{date[:4]}/{acc_clean}/{desc}"
                results.append({
                    "form": form,
                    "date": date,
                    "description": desc,
                    "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}&dateb=&owner=include&count=10",
                    "accession": acc,
                })
                if len(results) >= 5:
                    break

        return results
    except Exception:
        return []


def get_filing_summary(symbol: str) -> str:
    """Return a plain-text summary of the company's latest filings for AI ingestion."""
    filings = get_recent_filings(symbol)
    if not filings:
        return f"No recent SEC filings found for {symbol}."

    lines = [f"Recent SEC filings for {symbol}:"]
    for f in filings:
        lines.append(f"  - {f['form']} filed on {f['date']}: {f['description']}")
    return "\n".join(lines)
