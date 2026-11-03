"""Scrape a table (or list of elements) from a web page into a DataFrame."""
import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
# Used when the requested selector matches nothing: show the page's text instead.
TEXT_SELECTOR = "h1, h2, h3, h4, h5, p, li"


def _nothing_matched(soup, selector):
    """Explain why a selector failed and suggest a working one."""
    tables = len(soup.find_all("table"))
    text = soup.get_text(" ", strip=True)
    msg = f"No elements matched {selector!r}."
    if tables:
        msg += f" This page has {tables} <table> element(s); try the selector 'table tr'."
    else:
        msg += (" This page has no <table> elements (it may be a landing page instead of a data table). "
                "Try a selector for headings, list items or cards, such as 'h2', 'h3', 'li' or 'article'.")
    if len(text) < 200:
        msg += (" The downloaded HTML is almost empty, so the content is probably rendered by JavaScript. "
                "The scraper cannot run JavaScript; open the page in a browser and copy the data, or use "
                "the site's API/export instead.")
    return ValueError(msg)


def _text_frame(soup):
    """Extract visible headings, paragraphs and list items as a two-column table."""
    rows, seen = [], set()
    skip = {"nav", "script", "style", "noscript", "form"}
    for el in soup.select(TEXT_SELECTOR):
        if el.find_parent(list(skip)) or el.get("aria-hidden") == "true":
            continue
        text = el.get_text(" ", strip=True)
        if len(text) < 2 or text in seen:
            continue
        seen.add(text)
        rows.append([el.name, text])
    if not rows:
        raise _nothing_matched(soup, TEXT_SELECTOR)
    return pd.DataFrame(rows, columns=["element", "text"])


def scrape(url, selector="table tr", timeout=30, text_fallback=True):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"Could not fetch {url}: HTTP {resp.status_code}") from e
    soup = BeautifulSoup(resp.text, "html.parser")
    selector = (selector or "table tr").strip()
    elements = soup.select(selector)

    if not elements:
        if text_fallback:
            df = _text_frame(soup)
            df.attrs["fallback"] = (
                f"No elements matched {selector!r}, so the page text was extracted instead "
                f"({len(df)} blocks). Use 'table tr' when the page has a real table."
            )
            return df
        raise _nothing_matched(soup, selector)

    rows = []
    seen = set()
    for el in elements:
        cells = el.find_all(["th", "td"])
        if cells:
            row = [c.get_text(" ", strip=True) for c in cells]
        else:
            text = el.get_text(" ", strip=True)
            if not text or text in seen:  # drop duplicate headings/blocks
                continue
            seen.add(text)
            row = [text]
        rows.append(row)
    if not rows:
        raise _nothing_matched(soup, selector)
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header = rows[0]
    if len(rows) > 1 and all(header) and len(set(header)) == len(header):
        return pd.DataFrame(rows[1:], columns=header)
    return pd.DataFrame(rows, columns=[f"col{i + 1}" for i in range(width)])
