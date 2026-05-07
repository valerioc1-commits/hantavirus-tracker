# =============================================================
# clean.py — Hantavirus Tracker Data Cleaning Script
# What it does:
#   1. Reads all raw CSVs from data/raw/
#   2. Extracts structured numbers from text summaries
#   3. Standardizes country and date formats
#   4. Outputs one clean CSV to data/cleaned/
#   5. Outputs one master CSV that appends over time
# =============================================================

import pandas as pd
import os
import re
import json
from datetime import datetime
from glob import glob

# =============================================================
# PATHS
# =============================================================

RAW_PATH     = "../data/raw/"
CLEANED_PATH = "../data/cleaned/"
LOG_PATH     = "../logs/"

# =============================================================
# COUNTRY NAME STANDARDIZATION
# Maps messy variations → clean standard name
# We'll keep adding to this as new countries appear
# =============================================================

COUNTRY_MAP = {
    "usa"           : "United States",
    "u.s."          : "United States",
    "u.s.a."        : "United States",
    "united states" : "United States",
    "us"            : "United States",
    "argentina"     : "Argentina",
    "chile"         : "Chile",
    "brazil"        : "Brazil",
    "brasil"        : "Brazil",
    "bolivia"       : "Bolivia",
    "panama"        : "Panama",
    "paraguay"      : "Paraguay",
    "uruguay"       : "Uruguay",
    "peru"          : "Peru",
    "colombia"      : "Colombia",
    "venezuela"     : "Venezuela",
    "multi-country" : "Multi-country",
    "global"        : "Global",
}

# =============================================================
# HELPERS
# =============================================================

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}"
    print(entry)
    os.makedirs(LOG_PATH, exist_ok=True)
    with open(os.path.join(LOG_PATH, "cleaning_log.txt"), "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def standardize_country(raw_country):
    """
    Converts messy country text to a standard name.
    Example: 'USA' → 'United States'
    """
    if pd.isna(raw_country) or not raw_country:
        return None
    key = str(raw_country).strip().lower()
    return COUNTRY_MAP.get(key, str(raw_country).strip().title())


def parse_date(raw_date):
    """
    Tries multiple date formats and returns a clean YYYY-MM-DD string.
    Power BI needs consistent date formatting to build time series.
    """
    if pd.isna(raw_date) or not raw_date:
        return None

    raw_date = str(raw_date).strip()

    # List of formats to try — order matters, most specific first
    formats = [
        "%Y-%m-%dT%H:%M:%S",       # 2026-05-07T09:25:26
        "%Y-%m-%d",                 # 2026-05-07
        "%a, %d %b %Y %H:%M:%S %z",# Wed, 07 May 2026 09:00:00 +0000
        "%a, %d %b %Y %H:%M:%S GMT",
        "%d %b %Y",                 # 07 May 2026
        "%B %d, %Y",                # May 07, 2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # If none matched, return as-is — we'll catch it manually
    return raw_date


def extract_cases_from_text(text):
    """
    Searches free text for patterns like:
      '7 confirmed cases', '3 deaths', 'two laboratory-confirmed'
    Returns (cases, deaths) as integers or None if not found.

    This is called 'regex extraction' — regex = pattern matching in text.
    """
    if pd.isna(text) or not text:
        return None, None

    text = str(text).lower()

    # ── Confirmed cases patterns ─────────────────────────────
    case_patterns = [
        r'(\d+)\s+(?:confirmed\s+)?(?:laboratory[- ]confirmed\s+)?cases?',
        r'(?:total\s+of\s+)?(\d+)\s+(?:human\s+)?cases?',
        r'cases?[:\s]+(\d+)',
        r'(\d+)\s+(?:suspected|probable)\s+cases?',
    ]

    # ── Death patterns ───────────────────────────────────────
    death_patterns = [
        r'(\d+)\s+deaths?',
        r'(\d+)\s+(?:fatal|fatalities)',
        r'(\d+)\s+(?:people\s+)?(?:have\s+)?died',
        r'deaths?[:\s]+(\d+)',
        r'(\d+)\s+(?:have\s+)?died',
    ]

    confirmed_cases  = None
    confirmed_deaths = None

    for pattern in case_patterns:
        match = re.search(pattern, text)
        if match:
            confirmed_cases = int(match.group(1))
            break

    for pattern in death_patterns:
        match = re.search(pattern, text)
        if match:
            confirmed_deaths = int(match.group(1))
            break

    return confirmed_cases, confirmed_deaths


def extract_country_from_text(text, title):
    """
    Looks for country mentions in text/title.
    Falls back gracefully if nothing is found.
    """
    if pd.isna(text):
        text = ""
    if pd.isna(title):
        title = ""

    combined = (str(title) + " " + str(text)).lower()

    # Check our known country list against the text
    for key, standard_name in COUNTRY_MAP.items():
        if key in combined:
            return standard_name

    return None


def parse_cdc_summary(summary_json):
    """
    CDC records were saved as JSON strings in the summary column.
    This unpacks them into usable fields.
    """
    try:
        record = json.loads(summary_json)
        return {
            "cdc_group"      : record.get("group", None),
            "cdc_state"      : record.get("state", None),
            "cdc_start_date" : record.get("start_date", None),
            "cdc_end_date"   : record.get("end_date", None),
            "cdc_sex"        : record.get("sex", None),
            "cdc_data_as_of" : record.get("data_as_of", None),
        }
    except (json.JSONDecodeError, TypeError):
        return {}


# =============================================================
# MAIN CLEANING FUNCTION
# =============================================================

def clean_raw_file(filepath):
    """
    Takes one raw CSV file and returns a cleaned DataFrame.
    """
    log_message(f"Cleaning: {os.path.basename(filepath)}")

    try:
        df = pd.read_csv(filepath, encoding="utf-8")
        log_message(f"  Loaded {len(df)} rows, {len(df.columns)} columns.")
    except Exception as e:
        log_message(f"  ERROR loading file: {e}")
        return None

    cleaned_rows = []

    for _, row in df.iterrows():

        source      = row.get("source", "Unknown")
        title       = row.get("title", "")
        summary     = row.get("summary", "")
        url         = row.get("url", "")
        pub_date    = row.get("published_date", "")
        collected   = row.get("collected_at", "")
        strain      = row.get("strain", "Unknown")
        data_type   = row.get("data_type", "Unknown")
        raw_country = row.get("country", None)
        raw_state   = row.get("state_province", None)

        # ── Extract case/death numbers from text ─────────────
        # First check if raw columns already have numbers
        raw_cases  = row.get("confirmed_cases", None)
        raw_deaths = row.get("confirmed_deaths", None)

        if pd.isna(raw_cases) or pd.isna(raw_deaths):
            # Try to extract from summary text
            extracted_cases, extracted_deaths = extract_cases_from_text(summary)
            confirmed_cases  = extracted_cases  if pd.isna(raw_cases)  else raw_cases
            confirmed_deaths = extracted_deaths if pd.isna(raw_deaths) else raw_deaths
        else:
            confirmed_cases  = raw_cases
            confirmed_deaths = raw_deaths

        # ── Standardize country ──────────────────────────────
        country = standardize_country(raw_country)
        if not country:
            country = extract_country_from_text(summary, title)

        # ── Parse dates ──────────────────────────────────────
        clean_pub_date   = parse_date(pub_date)
        clean_collect_dt = parse_date(collected)

        # ── Handle CDC-specific fields ───────────────────────
        cdc_fields = {}
        if "CDC" in str(source):
            cdc_fields = parse_cdc_summary(summary)
            # For CDC records, state is more reliable than country text
            if cdc_fields.get("cdc_state"):
                raw_state = cdc_fields["cdc_state"]
            if not country:
                country = "United States"
            # Use CDC's disease group as strain context
            if cdc_fields.get("cdc_group"):
                strain = cdc_fields["cdc_group"]
            # Use CDC's start_date as published date if missing
            if not clean_pub_date and cdc_fields.get("cdc_start_date"):
                clean_pub_date = parse_date(cdc_fields["cdc_start_date"])

        # ── Build clean row ──────────────────────────────────
        clean_row = {
            # Identity
            "source"           : source,
            "data_type"        : data_type,
            "url"              : url,

            # Content
            "title"            : str(title).strip() if title else None,
            "strain"           : strain,

            # Numbers — what Power BI will visualize
            "confirmed_cases"  : confirmed_cases,
            "confirmed_deaths" : confirmed_deaths,

            # Geography — what Power BI maps will use
            "country"          : country,
            "state_province"   : str(raw_state).strip() if raw_state and not pd.isna(raw_state) else None,

            # Dates — what Power BI time series will use
            "published_date"   : clean_pub_date,
            "collected_at"     : clean_collect_dt,

            # Calculated field for Power BI
            "case_fatality_rate" : (
                round((confirmed_deaths / confirmed_cases) * 100, 1)
                if confirmed_cases and confirmed_deaths
                and confirmed_cases > 0
                else None
            ),

            # Source traceability
            "source_file"      : os.path.basename(filepath),
        }

        # Add CDC-specific columns if present
        clean_row.update(cdc_fields)
        cleaned_rows.append(clean_row)

    clean_df = pd.DataFrame(cleaned_rows)
    log_message(f"  Cleaned → {len(clean_df)} rows.")
    return clean_df


# =============================================================
# MASTER DATASET — Appends all runs over time
# This is what Power BI will connect to permanently
# =============================================================

def update_master_dataset(new_df, master_path):
    """
    Appends new cleaned data to the master CSV.
    Deduplicates by URL so we never double-count.
    """
    if os.path.exists(master_path):
        existing_df = pd.read_csv(master_path, encoding="utf-8")
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    # Deduplicate — same URL = same report
    before = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=["url"], keep="last")
    after  = len(combined_df)

    if before != after:
        log_message(f"  Removed {before - after} duplicate rows from master.")

    combined_df.to_csv(master_path, index=False, encoding="utf-8")
    log_message(f"  Master dataset updated: {after} total unique records.")
    return combined_df


# =============================================================
# MAIN
# =============================================================

def main():
    log_message("=" * 55)
    log_message("HANTAVIRUS TRACKER — Data Cleaning Started")
    log_message("=" * 55)

    # Find all raw CSV files
    raw_files = glob(os.path.join(RAW_PATH, "*.csv"))
    log_message(f"Found {len(raw_files)} raw CSV file(s) to process.")

    if not raw_files:
        log_message("No raw files found. Run collect.py first.")
        return

    os.makedirs(CLEANED_PATH, exist_ok=True)
    all_cleaned = []

    # Clean each raw file
    for filepath in raw_files:
        cleaned_df = clean_raw_file(filepath)
        if cleaned_df is not None and not cleaned_df.empty:
            all_cleaned.append(cleaned_df)

    if not all_cleaned:
        log_message("No data was successfully cleaned.")
        return

    # Combine all cleaned DataFrames
    combined = pd.concat(all_cleaned, ignore_index=True)

    # Save today's cleaned snapshot
    today     = datetime.now().strftime("%Y-%m-%d")
    snap_path = os.path.join(CLEANED_PATH, f"hantavirus_cleaned_{today}.csv")
    combined.to_csv(snap_path, index=False, encoding="utf-8")
    log_message(f"Today's snapshot saved → {snap_path}")

    # Update the master dataset (this is what Power BI connects to)
    master_path = os.path.join(CLEANED_PATH, "hantavirus_master.csv")
    master_df   = update_master_dataset(combined, master_path)

    # Print a summary of what's in the master
    log_message("-" * 55)
    log_message("MASTER DATASET SUMMARY:")
    log_message(f"  Total records     : {len(master_df)}")
    log_message(f"  Records with cases: {master_df['confirmed_cases'].notna().sum()}")
    log_message(f"  Records with deaths:{master_df['confirmed_deaths'].notna().sum()}")
    log_message(f"  Countries found   : {master_df['country'].nunique()}")
    log_message(f"  Date range        : {master_df['published_date'].min()} → {master_df['published_date'].max()}")
    log_message("-" * 55)

    log_message("Cleaning complete.")
    log_message("=" * 55)


if __name__ == "__main__":
    main()