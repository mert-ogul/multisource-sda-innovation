"""SDA category definitions and predefined opportunity themes."""

from enum import Enum


class SDACategory(str, Enum):
    AIR = "Air"
    KITCHEN = "Kitchen"
    COFFEE = "Coffee"
    FLOOR_CARE = "Floor Care"
    ROBOTICS = "Robotics"


class TimeWindow(str, Enum):
    ONE_YEAR = "Last 1 year"
    TWO_YEARS = "Last 2 years"
    THREE_YEARS = "Last 3 years"
    ALL = "All sample data"


TIME_WINDOW_YEARS: dict[TimeWindow, int | None] = {
    TimeWindow.ONE_YEAR: 1,
    TimeWindow.TWO_YEARS: 2,
    TimeWindow.THREE_YEARS: 3,
    TimeWindow.ALL: None,
}


PREDEFINED_THEMES: dict[SDACategory, list[str]] = {
    SDACategory.AIR: [
        "Silent compact air purifier for small bedrooms",
        "Low-energy HEPA filter for allergy sufferers in apartments",
    ],
    SDACategory.KITCHEN: [
        "Air fryer optimized for solo cooking and low energy use",
        "Compact dishwasher for studio kitchens",
    ],
    SDACategory.COFFEE: [
        "Easy-clean espresso machine for small kitchens",
        "Quiet single-serve coffee maker for early mornings",
    ],
    SDACategory.FLOOR_CARE: [
        "Pet-hair vacuum for small apartments with low noise at night",
        "Cordless stick vacuum with self-cleaning brush roll",
    ],
    SDACategory.ROBOTICS: [
        "Affordable robot vacuum with obstacle avoidance for cluttered homes",
        "Robot mop for hard floors in pet-friendly apartments",
    ],
}
