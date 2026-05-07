# =============================================================
# collect.py — Hantavirus Tracker v3 (Fixed)
# Fixes:
#   1. WHO: Now directly fetches known DON pages + keyword search
#   2. CDC: Deduplication now uses record-level ID not URL
#   3. WHO DON: Now fetches the actual outbreak item pages
# =============================================================

import feedparser
import requests
import pandas as pd
import os
import json
from datetime import datetime
from bs4 import BeautifulSoup

# =============================================================
# CONFIGURATION
# =============================================================

WHO_RSS_URL   = "https://www.who.int/rss-feeds/news-english.xml"
WHO_DON_BASE  = "https://www.who.int/emergencies/disease-outbreak-news"

# Known active Hantavirus DON report URLs — we add these directly
# as new ones are published, we'll add them here
WHO_KNOWN_HANTA_URLS = [
    "https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON599",
]

CDC_API_URL = (
    "https://data.cdc.gov/resource/9bhg-hcku.json"
    "?$limit=1000"
    "&$where=upper(group)%20like%20%27%25HANTA%25%27"
)
# Fallback CDC URL (no filter) in case above returns 0
CDC_API_FALLBACK = "https://data.cdc.gov/resource/9bhg-hcku.json?$limit=50"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

RAW_DATA_PATH = "../data/raw/"
LOG_PATH      = "../logs/"

HANTA_KEYWORDS = [
    "hantavirus", "hanta", "andes virus", "andes strain",
    "hcps", "hps", "hondius", "hantaviral", "sin nombre",
    "hantaan", "seoul virus"
]

# =============================================================
# HELPERS
# =============================================================

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    os.makedirs(LOG_PATH, exist_ok=True)
    with open(os.path.join(LOG_PATH, "collection_log.txt"), "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def is_hantavirus_related(text):
    text_lower = str(text).lower()
    return any(kw in text_lower for kw in HANTA_KEYWORDS)

def save_to_csv(data, prefix):
    if not data:
        log_message(f"No data to save for {prefix}.")
        return None
    os.makedirs(RAW_DATA_PATH, exist_ok=True)
    ts       = datetime.now().strftime("%Y-%m-%d_%H00")
    filepath = os.path.join(RAW_DATA_PATH, f"{prefix}_{ts}.csv")
    pd.DataFrame(data).to_csv(filepath, index=False, encoding="utf-8")
    log_message(f"✅ Saved {len(data)} records → {filepath}")
    return filepath

def empty_record(source, data_type):
    """Returns a blank record template so every row has the same columns."""
    return {
        "source"           : source,
        "title"            : None,
        "summary"          : None,
        "url"              : None,
        "published_date"   : None,
        "collected_at"     : datetime.now().isoformat(),
        "confirmed_cases"  : None,
        "confirmed_deaths" : None,
        "country"          : None,
        "state_province"   : None,
        "strain"           : None,
        "data_type"        : data_type
    }


# =============================================================
# SOURCE 1: WHO News RSS
# =============================================================

def collect_who_rss():
    log_message("── SOURCE 1: WHO News RSS ──────────────────────")
    try:
        resp    = requests.get(WHO_RSS_URL, headers=HEADERS, timeout=15)
        feed    = feedparser.parse(resp.content)
        results = []

        for entry in feed.entries:
            title   = entry.get("title", "")
            summary = entry.get("summary", "")
            if is_hantavirus_related(title) or is_hantavirus_related(summary):
                rec = empty_record("WHO_RSS", "news_item")
                rec.update({
                    "title"          : title,
                    "summary"        : summary[:600],
                    "url"            : entry.get("link", ""),
                    "published_date" : entry.get("published", ""),
                    "strain"         : "Andes" if "andes" in (title+summary).lower() else "Unknown"
                })
                results.append(rec)

        log_message(f"WHO RSS: {len(results)} matches from {len(feed.entries)} total entries.")
        return results

    except Exception as e:
        log_message(f"ERROR — WHO RSS: {e}")
        return []


# =============================================================
# SOURCE 2: WHO Known DON Report Pages
# Fetches the actual text of confirmed DON outbreak reports
# =============================================================

def collect_who_don_pages():
    log_message("── SOURCE 2: WHO DON Report Pages ─────────────")
    results = []

    for url in WHO_KNOWN_HANTA_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            log_message(f"  DON page {url[-8:]} → HTTP {resp.status_code}")

            if resp.status_code != 200:
                continue

            soup    = BeautifulSoup(resp.content, "html.parser")

            # Extract the page title
            title_tag = soup.find("h1")
            title     = title_tag.get_text(strip=True) if title_tag else "WHO DON Report"

            # Extract all paragraph text for the summary
            paragraphs = soup.find_all("p")
            full_text  = " ".join(p.get_text(strip=True) for p in paragraphs)
            summary    = full_text[:800]   # First 800 chars

            # Try to find publication date
            date_tag = soup.find("span", class_=lambda c: c and "date" in c.lower())
            pub_date = date_tag.get_text(strip=True) if date_tag else None

            rec = empty_record("WHO_DON", "official_don_report")
            rec.update({
                "title"          : title,
                "summary"        : summary,
                "url"            : url,
                "published_date" : pub_date,
                "country"        : "Multi-country",
                "strain"         : "Andes" if "andes" in full_text.lower() else "Unknown"
            })
            results.append(rec)
            log_message(f"  ✅ Scraped: {title[:60]}")

        except Exception as e:
            log_message(f"  ERROR scraping {url}: {e}")

    log_message(f"WHO DON pages: {len(results)} reports collected.")
    return results


# =============================================================
# SOURCE 3: CDC Open Data API
# US disease surveillance — filters for Hantavirus
# =============================================================

def collect_cdc_api():
    log_message("── SOURCE 3: CDC Open Data API ─────────────────")
    try:
        # Try filtered URL first
        resp = requests.get(CDC_API_URL, headers=HEADERS, timeout=15)
        log_message(f"CDC filtered API status: {resp.status_code}")
        data = resp.json() if resp.status_code == 200 else []

        # If filter returns nothing, use fallback and filter manually
        if not data:
            log_message("CDC filtered query returned 0 — trying fallback...")
            resp2 = requests.get(CDC_API_FALLBACK, headers=HEADERS, timeout=15)
            raw   = resp2.json() if resp2.status_code == 200 else []
            data  = [r for r in raw if is_hantavirus_related(json.dumps(r))]
            log_message(f"CDC fallback: {len(data)} hantavirus matches from manual filter.")

        results = []
        for i, record in enumerate(data):
            rec = empty_record("CDC_API", "surveillance_record")
            rec.update({
                # Use index + disease + state as a unique row identifier
                "title"          : f"CDC | {record.get('disease','?')} | {record.get('state','?')} | {record.get('start_date','?')}",
                "summary"        : json.dumps(record),
                "url"            : f"https://data.cdc.gov/resource/9bhg-hcku#{i}",  # Unique URL per row
                "published_date" : record.get("data_as_of", None),
                "country"        : "United States",
                "state_province" : record.get("state", None),
                "strain"         : "Unknown"
            })
            results.append(rec)

        log_message(f"CDC API: {len(results)} records collected.")
        return results

    except Exception as e:
        log_message(f"ERROR — CDC API: {e}")
        return []


# =============================================================
# MAIN
# =============================================================

def main():
    log_message("=" * 55)
    log_message("HANTAVIRUS TRACKER — Collection Run Started")
    log_message("=" * 55)

    who_rss  = collect_who_rss()
    who_don  = collect_who_don_pages()
    cdc      = collect_cdc_api()

    all_data = who_rss + who_don + cdc

    # Deduplicate by URL (now safe because CDC rows have unique URLs)
    seen, unique = set(), []
    for item in all_data:
        url = item.get("url", "")
        if url not in seen:
            seen.add(url)
            unique.append(item)

    log_message("-" * 55)
    log_message(f"SUMMARY:")
    log_message(f"  WHO RSS:       {len(who_rss)} records")
    log_message(f"  WHO DON pages: {len(who_don)} records")
    log_message(f"  CDC API:       {len(cdc)} records")
    log_message(f"  Total unique:  {len(unique)} records")
    log_message("-" * 55)

    save_to_csv(unique, "hantavirus_raw")

    log_message("Collection run complete.")
    log_message("=" * 55)

if __name__ == "__main__":
    main()