import pandas as pd
import os
from datetime import datetime

CLEANED_PATH = "../data/cleaned/"

seed_records = [
    {
        "source": "WHO_DON_MANUAL",
        "data_type": "confirmed_outbreak",
        "url": "https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON599#cluster-total",
        "title": "Hantavirus cluster linked to cruise ship travel - Multi-country",
        "strain": "Andes",
        "confirmed_cases": 7,
        "confirmed_deaths": 3,
        "country": "Multi-country",
        "state_province": None,
        "published_date": "2026-05-04",
        "collected_at": datetime.now().strftime("%Y-%m-%d"),
        "case_fatality_rate": 42.9,
        "source_file": "seed_data_manual.csv"
    },
    {
        "source": "WHO_DON_MANUAL",
        "data_type": "confirmed_outbreak",
        "url": "https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON599#argentina",
        "title": "Hantavirus - Andes strain exposure - Argentina",
        "strain": "Andes",
        "confirmed_cases": 2,
        "confirmed_deaths": 1,
        "country": "Argentina",
        "state_province": None,
        "published_date": "2026-05-04",
        "collected_at": datetime.now().strftime("%Y-%m-%d"),
        "case_fatality_rate": 50.0,
        "source_file": "seed_data_manual.csv"
    },
    {
        "source": "WHO_DON_MANUAL",
        "data_type": "confirmed_outbreak",
        "url": "https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON599#critical",
        "title": "Hantavirus - Critical case - International",
        "strain": "Andes",
        "confirmed_cases": 1,
        "confirmed_deaths": 0,
        "country": "Multi-country",
        "state_province": None,
        "published_date": "2026-05-04",
        "collected_at": datetime.now().strftime("%Y-%m-%d"),
        "case_fatality_rate": 0.0,
        "source_file": "seed_data_manual.csv"
    }
]

def main():
    os.makedirs(CLEANED_PATH, exist_ok=True)

    seed_df = pd.DataFrame(seed_records)
    seed_path = os.path.join(CLEANED_PATH, "seed_data_manual.csv")
    seed_df.to_csv(seed_path, index=False, encoding="utf-8")
    print("Seed data saved: " + str(len(seed_df)) + " records")

    master_path = os.path.join(CLEANED_PATH, "hantavirus_master.csv")
    if os.path.exists(master_path):
        master_df = pd.read_csv(master_path, encoding="utf-8")
        combined = pd.concat([master_df, seed_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["url"], keep="last")
    else:
        combined = seed_df

    combined.to_csv(master_path, index=False, encoding="utf-8")
    print("Master updated: " + str(len(combined)) + " total records")
    print(combined[["country", "confirmed_cases", "confirmed_deaths"]].to_string())

if __name__ == "__main__":
    main()