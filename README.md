\# 🦠 Hantavirus Outbreak Tracker



Real-time global Hantavirus case tracking dashboard — built with Python, GitHub Actions, and Power BI.



\## 📡 Data Sources

\- WHO Disease Outbreak News (official reports)

\- WHO News RSS Feed

\- CDC Open Data API (US surveillance)



\## 🔄 Update Frequency

Data is collected automatically every hour via GitHub Actions.



\## 📁 Repository Structure

\- `data/raw/` — Hourly raw CSV snapshots from all sources

\- `data/cleaned/` — Processed data ready for Power BI

\- `scripts/collect.py` — Data collection pipeline

\- `scripts/clean.py` — Data cleaning and transformation (Step 2)

\- `logs/` — Collection run logs

\- `dashboard/` — Power BI dashboard files (Step 3)



\## 🛠️ Tech Stack

Python · pandas · BeautifulSoup · feedparser · GitHub Actions · Power BI



\## 📊 Dashboard Features (In Progress)

\- Global confirmed cases map

\- US state-level breakdown

\- Trend lines over time

\- Filters by country, date, strain



\## 🚧 Project Status

\- \[x] Step 1: Data pipeline and automation

\- \[ ] Step 2: Data cleaning and modeling

\- \[ ] Step 3: Power BI visualizations

\- \[ ] Step 4: Dashboard deployment

