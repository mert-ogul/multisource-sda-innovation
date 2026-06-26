"""USPTO search terms per SDA category."""

from __future__ import annotations

# Primary USPTO title-search phrases per SDA category (most specific first).
CATEGORY_PATENT_SEARCH_TERMS: dict[str, list[str]] = {
    "Air": ["air purifier", "HEPA", "air cleaner"],
    "Kitchen": ["air fryer", "countertop oven", "kitchen appliance"],
    "Coffee": ["coffee maker", "espresso machine", "coffee brewing"],
    "Floor Care": ["vacuum cleaner", "cordless vacuum", "pet hair vacuum"],
    "Robotics": ["robot vacuum", "robotic vacuum", "autonomous floor"],
}
