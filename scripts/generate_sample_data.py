"""Deterministic sample data for offline demo mode.

Anchor opportunity themes (realistic SDA examples):
  - Air purifier for small bedrooms
  - Air fryer for solo / low-energy cooking
  - Easy-clean espresso / coffee machine
  - Pet-hair vacuum and robot vacuum for apartments
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"

RNG = np.random.default_rng(42)
REGIONS = ["US", "EU", "UK", "APAC"]

# category, theme label (for documentation), primary keywords
ANCHOR_THEMES: list[tuple[str, str, list[str]]] = [
    ("Air", "Silent compact air purifier for small bedrooms", ["hepa", "quiet", "bedroom", "compact"]),
    ("Kitchen", "Air fryer optimized for solo cooking and low energy use", ["air fryer", "solo", "energy", "compact"]),
    ("Coffee", "Easy-clean espresso machine for small kitchens", ["espresso", "easy clean", "kitchen", "maintenance"]),
    ("Floor Care", "Pet-hair vacuum for small apartments with low noise at night", ["pet hair", "quiet", "apartment", "cordless"]),
    ("Robotics", "Affordable robot vacuum with obstacle avoidance for cluttered homes", ["robot vacuum", "obstacle", "apartment", "navigation"]),
]


def _dates(n: int, start_year: int = 2023) -> list[date]:
    """Spread dates across recent years so time-window filters work in demos."""
    base = date(start_year, 1, 1)
    span_days = max((date.today() - base).days, 365 * 3)
    return [base + timedelta(days=int(RNG.integers(0, span_days))) for _ in range(n)]


def _patents_df() -> pd.DataFrame:
    rows = [
        ("EP4012345", "Low-noise HEPA air purifier for compact bedrooms", "A compact air purification device with noise-dampened fan assembly and HEPA filtration for small bedrooms and apartments.", "Philips Domestic", "Air", "EU", ["hepa", "quiet", "compact", "bedroom"]),
        ("US11234567", "Energy-efficient air fryer for single-portion cooking", "An air fryer optimized for solo meals with reduced power draw and rapid preheat.", "Breville Group", "Kitchen", "US", ["air fryer", "energy", "solo", "compact"]),
        ("EP3890123", "Self-cleaning espresso brew group for small kitchens", "Espresso machine with removable brew group and automated rinse cycle for easy maintenance.", "De'Longhi", "Coffee", "EU", ["espresso", "easy clean", "kitchen", "maintenance"]),
        ("US10987654", "Quiet cordless vacuum with pet hair brush", "Stick vacuum featuring acoustic insulation and anti-tangle brush for pet hair on hard floors.", "Dyson", "Floor Care", "UK", ["pet hair", "quiet", "cordless", "apartment"]),
        ("EP3756789", "Obstacle-aware robot vacuum for cluttered homes", "SLAM-based navigation with low-profile form factor for furniture clearance.", "iRobot", "Robotics", "US", ["robot vacuum", "obstacle", "apartment", "navigation"]),
        ("US10543210", "Smart air purifier with PM2.5 sensor", "IoT-enabled purifier with auto mode and filter life tracking for urban bedrooms.", "Blueair", "Air", "US", ["smart", "pm2.5", "filter", "bedroom"]),
        ("EP3398765", "Oil-free air fryer with dual heating elements", "Dual-element air fryer reducing cook time and energy for small households.", "Ninja", "Kitchen", "UK", ["air fryer", "energy", "dual heat", "solo"]),
        ("US10432109", "Portable espresso with easy-clean drip tray", "Compact espresso using recyclable pods and drip tray easy removal.", "Lavazza", "Coffee", "US", ["espresso", "portable", "easy", "kitchen"]),
        ("EP3409876", "Bagless vacuum with HEPA exhaust for allergies", "Cylinder vacuum with sealed HEPA path for allergy sufferers in small homes.", "Miele", "Floor Care", "EU", ["hepa", "allergy", "quiet", "compact"]),
        ("EP3287654", "Robot vacuum with self-empty base", "Docking station with bagged auto-empty for low maintenance in pet homes.", "Shark", "Robotics", "US", ["robot vacuum", "self empty", "pet", "apartment"]),
    ]
    records = []
    for pid, title, abstract, applicant, cat, region, kws in rows:
        records.append({
            "patent_id": pid,
            "title": title,
            "abstract": abstract,
            "applicant": applicant,
            "filing_date": _dates(1)[0].isoformat(),
            "category": cat,
            "region": region,
            "keywords": ",".join(kws),
        })
    for _ in range(25):
        base = rows[int(RNG.integers(0, len(rows)))]
        records.append({
            "patent_id": f"EP{RNG.integers(3000000, 4999999)}",
            "title": base[1],
            "abstract": base[2],
            "applicant": base[3],
            "filing_date": _dates(1)[0].isoformat(),
            "category": base[4],
            "region": REGIONS[int(RNG.integers(0, 4))],
            "keywords": ",".join(base[6]),
        })
    df = pd.DataFrame(records)
    df["filing_date"] = pd.to_datetime(df["filing_date"]).dt.date
    return df


def _news_df() -> pd.DataFrame:
    headlines = [
        ("Philips launches whisper-quiet bedroom air purifier", "New compact HEPA unit targets urban apartments with sub-25dB night mode.", "TechHome", "Air", "EU"),
        ("Solo living drives demand for smaller air fryers", "Manufacturers race to ship energy-efficient 2L models for one-person households.", "Appliance Weekly", "Kitchen", "US"),
        ("De'Longhi bets on easy-clean espresso for millennials", "Removable brew groups and auto-rinse aim to reduce maintenance friction.", "Coffee Insider", "Coffee", "EU"),
        ("Dyson unveils quieter stick vacuum for pet owners", "Acoustic redesign promises 40% noise reduction during evening cleaning.", "Home Gadgets", "Floor Care", "UK"),
        ("Robot vacuums get smarter obstacle avoidance in 2024", "iRobot and Roborock compete on cluttered-home navigation.", "Robotics Today", "Robotics", "US"),
        ("Allergy season boosts HEPA purifier sales in cities", "Retailers report surge in compact models for bedrooms.", "Retail Pulse", "Air", "US"),
        ("Energy labels push kitchen brands toward efficient air fryers", "EU regulations accelerate low-power solo cooking appliances.", "Green Appliance", "Kitchen", "EU"),
        ("Nespresso quiet brew tech wins design award", "Morning-friendly coffee makers gain traction in open-plan studios.", "Design Brew", "Coffee", "US"),
        ("Apartment dwellers want night-mode vacuum cleaners", "Survey: noise is top pain point for pet-hair vacuum purchases.", "Consumer Voice", "Floor Care", "APAC"),
        ("Budget robot vacuums enter mass market for apartments", "Sub-$300 bots target cluttered pet-friendly homes.", "Smart Home Mag", "Robotics", "APAC"),
    ]
    records = []
    for h, snippet, source, cat, region in headlines:
        records.append({
            "headline": h,
            "snippet": snippet,
            "source_name": source,
            "published_date": _dates(1)[0].isoformat(),
            "category": cat,
            "region": region,
            "entities": h.split()[0],
        })
    for _ in range(20):
        base = headlines[int(RNG.integers(0, len(headlines)))]
        records.append({
            "headline": base[0],
            "snippet": base[1],
            "source_name": base[2],
            "published_date": _dates(1)[0].isoformat(),
            "category": base[3],
            "region": REGIONS[int(RNG.integers(0, 4))],
            "entities": base[0].split()[0],
        })
    df = pd.DataFrame(records)
    df["published_date"] = pd.to_datetime(df["published_date"]).dt.date
    return df


def _reviews_df() -> pd.DataFrame:
    reviews = [
        ("QuietAir Mini", "Love how silent it is at night but filter replacements are pricey.", 4.0, "Air", "US"),
        ("SoloFry 2L", "Perfect for one person, uses less energy than my old oven.", 4.5, "Kitchen", "EU"),
        ("CleanShot Espresso", "Easy to clean brew group but water tank is awkward in a tiny kitchen.", 3.5, "Coffee", "UK"),
        ("PetQuiet Stick", "Picks up dog hair well but still a bit loud on max power at night.", 3.0, "Floor Care", "US"),
        ("NavigateBot S", "Handles cluttered apartment well; misses corners sometimes.", 4.0, "Robotics", "APAC"),
        ("Bedroom HEPA Pro", "Allergies improved but unit is bulky for a small bedroom.", 3.5, "Air", "EU"),
        ("EcoFry Compact", "Great air fryer for solo cooking; basket is small for guests.", 4.0, "Kitchen", "US"),
        ("MorningBrew Quiet", "Finally an espresso machine that doesn't wake my partner.", 4.5, "Coffee", "US"),
        ("NightVacuum Lite", "Night mode is quieter for apartment use but suction drops.", 3.0, "Floor Care", "UK"),
        ("ClutterBot X", "Best robot vacuum I've tried for shoes and cables in a small flat.", 4.0, "Robotics", "EU"),
    ]
    records = []
    for product, text, rating, cat, region in reviews:
        records.append({
            "product_name": product,
            "review_text": text,
            "rating": rating,
            "review_date": _dates(1)[0].isoformat(),
            "category": cat,
            "region": region,
        })
    for _ in range(40):
        base = reviews[int(RNG.integers(0, len(reviews)))]
        records.append({
            "product_name": base[0],
            "review_text": base[1],
            "rating": float(RNG.choice([2.5, 3.0, 3.5, 4.0, 4.5])),
            "review_date": _dates(1)[0].isoformat(),
            "category": base[3],
            "region": REGIONS[int(RNG.integers(0, 4))],
        })
    df = pd.DataFrame(records)
    df["review_date"] = pd.to_datetime(df["review_date"]).dt.date
    return df


def _social_df() -> pd.DataFrame:
    posts = [
        ("Best quiet air purifier for studio apartment?", "Need something silent for bedroom under 200. HEPA a must.", "reddit", "Air", "US", 142, 38),
        ("Air fryer for one person — energy use?", "Solo living, hate preheating a full oven. Recommendations?", "reddit", "Kitchen", "EU", 89, 52),
        ("Espresso machine that isn't a pain to clean?", "Small kitchen, hate descaling and maintenance rituals.", "reddit", "Coffee", "UK", 201, 67),
        ("Vacuum for pet hair in apartment — quiet at night?", "Dog sheds a lot, neighbors complain about noise.", "reddit", "Floor Care", "US", 176, 44),
        ("Robot vacuum vs cluttered apartment", "Too many cables and shoes — which bot copes?", "reddit", "Robotics", "APAC", 95, 31),
        ("HEPA purifier worth it for allergies?", "Bedroom is 12sqm, worried about bulky units.", "reddit", "Air", "EU", 64, 22),
        ("Low energy air fryer brands?", "Electric bill went up, want efficient solo cooker.", "reddit", "Kitchen", "US", 55, 19),
        ("Easy clean coffee maker for tiny kitchen?", "Partner is a light sleeper, need simple maintenance.", "reddit", "Coffee", "US", 118, 41),
        ("Stick vacuum night mode experiences", "Does night mode actually help pet hair in apartments?", "reddit", "Floor Care", "UK", 73, 28),
        ("Robot vacuum obstacle avoidance — real world?", "Hard floors + golden retriever hair in small flat.", "reddit", "Robotics", "EU", 84, 25),
    ]
    records = []
    for title, body, platform, cat, region, up, comments in posts:
        records.append({
            "title": title,
            "body": body,
            "platform": platform,
            "posted_date": _dates(1)[0].isoformat(),
            "category": cat,
            "region": region,
            "upvotes": up,
            "comment_count": comments,
        })
    for _ in range(30):
        base = posts[int(RNG.integers(0, len(posts)))]
        records.append({
            "title": base[0],
            "body": base[1],
            "platform": base[2],
            "posted_date": _dates(1)[0].isoformat(),
            "category": base[3],
            "region": REGIONS[int(RNG.integers(0, 4))],
            "upvotes": int(RNG.integers(20, 250)),
            "comment_count": int(RNG.integers(5, 80)),
        })
    df = pd.DataFrame(records)
    df["posted_date"] = pd.to_datetime(df["posted_date"]).dt.date
    return df


def _catalog_df() -> pd.DataFrame:
    products = [
        ("P001", "QuietAir Mini HEPA", "Philips", "Air", "EU", 189.0, "hepa,yes;noise_db,22;compact,yes"),
        ("P002", "SoloFry 2L Energy Saver", "Ninja", "Kitchen", "US", 79.0, "capacity_l,2;energy_class,A+;solo,yes"),
        ("P003", "CleanShot Espresso Easy", "De'Longhi", "Coffee", "EU", 349.0, "easy_clean,yes;footprint,small"),
        ("P004", "PetQuiet Cordless", "Dyson", "Floor Care", "UK", 399.0, "pet_hair,yes;noise_rating,low"),
        ("P005", "NavigateBot S", "iRobot", "Robotics", "US", 449.0, "obstacle_avoid,yes;self_empty,no"),
        ("P006", "Bedroom HEPA Pro", "Blueair", "Air", "US", 229.0, "hepa,yes;night_mode,yes"),
        ("P007", "EcoFry Compact", "Breville", "Kitchen", "US", 99.0, "capacity_l,2.5;energy_class,A"),
        ("P008", "MorningBrew Silent", "Nespresso", "Coffee", "US", 159.0, "quiet,yes;easy_clean,yes"),
        ("P009", "NightVacuum Lite", "Shark", "Floor Care", "US", 249.0, "night_mode,yes;cordless,yes"),
        ("P010", "ClutterBot X", "Roborock", "Robotics", "APAC", 329.0, "obstacle_avoid,yes;apartment,yes"),
    ]
    records = []
    for row in products:
        records.append({
            "product_id": row[0],
            "name": row[1],
            "brand": row[2],
            "category": row[3],
            "region": row[4],
            "price_usd": row[5],
            "attributes": row[6],
        })
    for i in range(20):
        base = products[int(RNG.integers(0, len(products)))]
        records.append({
            "product_id": f"P{100 + i}",
            "name": f"{base[1]} v{i}",
            "brand": base[2],
            "category": base[3],
            "region": REGIONS[int(RNG.integers(0, 4))],
            "price_usd": float(base[5]) + float(RNG.integers(-30, 50)),
            "attributes": base[6],
        })
    return pd.DataFrame(records)


def generate_all(output_dir: Path | None = None) -> dict[str, Path]:
    """Write deterministic sample CSV/JSON files and return paths."""
    out = output_dir or SAMPLE_DIR
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "patents": out / "patents.csv",
        "news": out / "news.csv",
        "reviews": out / "reviews.csv",
        "social": out / "social.csv",
        "catalog": out / "product_catalog.csv",
    }
    _patents_df().to_csv(paths["patents"], index=False)
    _news_df().to_csv(paths["news"], index=False)
    _reviews_df().to_csv(paths["reviews"], index=False)
    _social_df().to_csv(paths["social"], index=False)
    _catalog_df().to_csv(paths["catalog"], index=False)

    meta = {
        "generated": date.today().isoformat(),
        "mode": "sample",
        "seed": 42,
        "anchor_themes": [{"category": c, "theme": t} for c, t, _ in ANCHOR_THEMES],
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2))
    return paths


if __name__ == "__main__":
    paths = generate_all()
    for name, p in paths.items():
        print(f"Wrote {name}: {p}")
