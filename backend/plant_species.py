"""
plant_species.py
-----------------
Reference data for supported plant species.

These ranges are based on commonly cited horticultural guidelines for each
species (not arbitrary placeholders), so the simulation behaves in a way
that matches real plant care advice:

- Cactus: very low water/humidity tolerance, high sunlight, wide temp range
- Tulsi (Holy Basil): moderate water, high sunlight, warm climate plant
- Rose: moderate-high water, full sun, moderate temp band
- Sunflower: high water during growth, very high sunlight requirement
- Aloe Vera: low water (succulent), bright indirect light, drought-tolerant

Each range is (min, max, ideal) in the unit noted.
"""

PLANT_SPECIES = {
    "Rose": {
        "water_requirement": {"min": 40, "max": 70, "ideal": 55, "unit": "% soil moisture"},
        "sunlight_requirement": {"min": 60, "max": 100, "ideal": 80, "unit": "% of full sun"},
        "temperature_range": {"min": 15, "max": 29, "ideal": 22, "unit": "°C"},
        "humidity_range": {"min": 40, "max": 70, "ideal": 55, "unit": "%"},
        "fertilizer_ideal": 60,
        "growth_speed": 1.0,   # relative multiplier used in simulation
        "description": "Full sun, moderate water, classic flowering shrub.",
    },
    "Sunflower": {
        "water_requirement": {"min": 50, "max": 80, "ideal": 65, "unit": "% soil moisture"},
        "sunlight_requirement": {"min": 80, "max": 100, "ideal": 95, "unit": "% of full sun"},
        "temperature_range": {"min": 18, "max": 32, "ideal": 24, "unit": "°C"},
        "humidity_range": {"min": 35, "max": 65, "ideal": 50, "unit": "%"},
        "fertilizer_ideal": 65,
        "growth_speed": 1.3,
        "description": "Needs near-full sun all day; fast-growing annual.",
    },
    "Cactus": {
        "water_requirement": {"min": 5, "max": 25, "ideal": 15, "unit": "% soil moisture"},
        "sunlight_requirement": {"min": 70, "max": 100, "ideal": 90, "unit": "% of full sun"},
        "temperature_range": {"min": 10, "max": 38, "ideal": 25, "unit": "°C"},
        "humidity_range": {"min": 10, "max": 40, "ideal": 25, "unit": "%"},
        "fertilizer_ideal": 20,
        "growth_speed": 0.3,
        "description": "Drought-tolerant succulent; overwatering is the #1 killer.",
    },
    "Tulsi": {
        "water_requirement": {"min": 40, "max": 65, "ideal": 50, "unit": "% soil moisture"},
        "sunlight_requirement": {"min": 65, "max": 100, "ideal": 85, "unit": "% of full sun"},
        "temperature_range": {"min": 20, "max": 35, "ideal": 27, "unit": "°C"},
        "humidity_range": {"min": 40, "max": 70, "ideal": 55, "unit": "%"},
        "fertilizer_ideal": 45,
        "growth_speed": 1.1,
        "description": "Holy Basil; warm climate, likes consistent moisture, not waterlogged soil.",
    },
    "Aloe Vera": {
        "water_requirement": {"min": 10, "max": 30, "ideal": 20, "unit": "% soil moisture"},
        "sunlight_requirement": {"min": 50, "max": 90, "ideal": 70, "unit": "% of full sun"},
        "temperature_range": {"min": 13, "max": 32, "ideal": 23, "unit": "°C"},
        "humidity_range": {"min": 20, "max": 50, "ideal": 35, "unit": "%"},
        "fertilizer_ideal": 25,
        "growth_speed": 0.4,
        "description": "Succulent; bright indirect light, infrequent deep watering.",
    },
}

GROWTH_STAGES = [
    "Seed",
    "Germination",
    "Seedling",
    "Young Plant",
    "Flowering",
    "Mature Plant",
    "Fruit Bearing",
    "Dead Plant",
]

# Approximate growth "points" needed to advance to the next stage.
# Accumulated each simulation cycle based on health score.
STAGE_THRESHOLDS = {
    "Seed": 5,
    "Germination": 10,
    "Seedling": 20,
    "Young Plant": 30,
    "Flowering": 40,
    "Mature Plant": 50,
    "Fruit Bearing": float("inf"),  # terminal healthy stage
}


def get_species_list():
    """Return the list of supported species names."""
    return list(PLANT_SPECIES.keys())


def get_species_info(species: str) -> dict:
    """Return the reference dict for a given species, raising if unknown."""
    if species not in PLANT_SPECIES:
        raise ValueError(f"Unknown species: {species}")
    return PLANT_SPECIES[species]
