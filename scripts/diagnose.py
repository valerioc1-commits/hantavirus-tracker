# =============================================================
# diagnose.py — Testing Updated Source URLs
# =============================================================

import feedparser
import requests
import json

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ── NEW SOURCE URLs ───────────────────────────────────────────
WHO_RSS_NEW      = "https://www.who.int/rss-feeds/news-english.xml"
RELIEFWEB_API    = "https://api.reliefweb.int/v1/reports?appname=hantavirus-tracker&filter[field]=disease&filter[value]=hantavirus&limit=10"
CDC_API          = "https://data.cdc.gov/resource/9bhg-hcku.json?$limit=5"

def test_rss(name, url):
    print("\n" + "=" * 60)
    print(f"TESTING RSS: {name}")
    print(f"URL: {url}")
    print("=" * 60)
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"HTTP Status: {response.status_code}")
        if response.status_code != 200:
            print("  FAILED — trying without headers...")
            response = requests.get(url, timeout=15)
            print(f"  Retry Status: {response.status_code}")
            if response.status_code != 200:
                return

        feed = feedparser.parse(response.content)
        print(f"Entries found: {len(feed.entries)}")
        if feed.entries:
            print("  ✅ FEED WORKS — Sample titles:")
            for e in feed.entries[:3]:
                print(f"    - {e.get('title','NO TITLE')[:80]}")
        else:
            print("  ⚠️  No entries returned")
    except Exception as ex:
        print(f"  ERROR: {ex}")


def test_json_api(name, url):
    print("\n" + "=" * 60)
    print(f"TESTING JSON API: {name}")
    print(f"URL: {url}")
    print("=" * 60)
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"HTTP Status: {response.status_code}")
        if response.status_code != 200:
            print("  FAILED")
            return
        data = response.json()
        # Handle both list responses and dict responses
        if isinstance(data, list):
            print(f"  ✅ API WORKS — {len(data)} records returned")
            if data:
                print(f"  Sample keys: {list(data[0].keys())[:6]}")
        elif isinstance(data, dict):
            print(f"  ✅ API WORKS — Response keys: {list(data.keys())}")
        else:
            print(f"  Unexpected response type: {type(data)}")
    except Exception as ex:
        print(f"  ERROR: {ex}")


# Run all tests
test_rss("WHO News (New URL)",    WHO_RSS_NEW)
test_json_api("ReliefWeb API",    RELIEFWEB_API)
test_json_api("CDC Open Data",    CDC_API)

print("\n" + "=" * 60)
print("Diagnosis complete — share screenshot with your mentor!")
print("=" * 60)