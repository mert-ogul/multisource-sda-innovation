"""Map synthetic appliance types to SDA categories."""

from __future__ import annotations

# Appliance Product Data – Synthetic Data Set types → SDA categories.
APPLIANCE_TYPE_TO_SDA: dict[str, str] = {
    "kettle": "Coffee",
    "toaster": "Kitchen",
    "dish washer": "Kitchen",
    "dishwasher": "Kitchen",
    "stove": "Kitchen",
    "freezer": "Kitchen",
    "dryer": "Kitchen",
    "washer": "Kitchen",
    "refrigerator": "Kitchen",
    # Future-friendly aliases if the dataset is extended.
    "air purifier": "Air",
    "purifier": "Air",
    "vacuum": "Floor Care",
    "robot vacuum": "Robotics",
    "coffee maker": "Coffee",
    "espresso": "Coffee",
}

SYNTHETIC_CATALOG_FILENAME = "appliance-skus-10k-synthetic.csv"

# SKU counts above these thresholds indicate a crowded vs. sparse niche.
CATALOG_CROWDING_THRESHOLDS = {
    "crowded": 800,
    "moderate": 300,
}
