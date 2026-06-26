"""Keyword filters for mapping external review datasets to SDA categories."""

from __future__ import annotations

# Keywords used to assign Amazon (and other) reviews to SDA categories.
# Order matters: more specific categories (Robotics) are checked before broader ones (Floor Care).
SDA_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Robotics": [
        "robot vacuum",
        "robot mop",
        "robotic vacuum",
        "roomba",
        "robot cleaner",
        "robot sweeper",
        "navigate bot",
    ],
    "Air": [
        "air purifier",
        "air cleaner",
        "hepa filter",
        "hepa",
        "purifier",
        "ionizer",
        "air quality",
    ],
    "Kitchen": [
        "air fryer",
        "airfryer",
        "deep fryer",
        "toaster oven",
        "countertop oven",
        "dishwasher",
        "instant pot",
        "slow cooker",
        "microwave oven",
    ],
    "Coffee": [
        "coffee maker",
        "coffeemaker",
        "coffee machine",
        "espresso machine",
        "espresso maker",
        "keurig",
        "french press",
        "coffee press",
        "cappuccino machine",
        "latte machine",
        "single serve coffee",
        "brew station",
        "drip coffee",
    ],
    "Floor Care": [
        "vacuum cleaner",
        "stick vacuum",
        "cordless vacuum",
        "upright vacuum",
        "pet hair vacuum",
        "hoover",
        "hand vacuum",
        "canister vacuum",
        "vacuum",
    ],
}

# Amazon PRODUCT_CATEGORY values that hint at SDA relevance before text matching.
AMAZON_CATEGORY_HINTS: dict[str, list[str]] = {
    "Kitchen": ["kitchen"],
    "Air": ["home", "appliances"],
    "Floor Care": ["home", "appliances"],
    "Coffee": ["kitchen", "grocery"],
    "Robotics": ["home", "appliances"],
}

USER_REVIEW_DATASETS = (
    "coffee_maker.csv",
    "amazon_reviews.txt",
    "ratings_and_sentiments.csv",
    "raw_yelp_review_data.csv",
)
