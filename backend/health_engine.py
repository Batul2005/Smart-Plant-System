"""
health_engine.py
-----------------
Computes a plant's health score (0-100) from its current environmental
readings and the ideal ranges for its species.

Approach:
Each factor (water, sunlight, temperature, humidity, fertilizer) is scored
individually based on how far the current reading is from the species'
ideal range, then combined with weights reflecting real horticultural
importance (water and sunlight matter more day-to-day than fertilizer).

This is a deterministic, explainable scoring system (not a black box),
which is what feeds BOTH the rule-based recommendation engine AND the
ML model's training labels.
"""

from backend.plant_species import get_species_info

# Relative importance of each factor in the overall health score.
FACTOR_WEIGHTS = {
    "water": 0.30,
    "sunlight": 0.25,
    "temperature": 0.20,
    "humidity": 0.15,
    "fertilizer": 0.10,
}


def _score_against_range(value: float, min_v: float, max_v: float, ideal_v: float) -> float:
    """
    Score a single reading 0-100 based on distance from the ideal value,
    scaled by how wide the acceptable range is.

    - At the ideal value: 100
    - At or beyond the min/max boundary: drops toward 40 (still alive, stressed)
    - Far beyond the boundary (>1.5x the range width past the edge): drops toward 0
    """
    range_width = max(max_v - min_v, 1e-6)

    if min_v <= value <= max_v:
        # Inside acceptable range: linear falloff from ideal
        distance = abs(value - ideal_v)
        max_distance = max(ideal_v - min_v, max_v - ideal_v, 1e-6)
        score = 100 - (distance / max_distance) * 40  # worst case inside range = 60
        return max(score, 60)

    # Outside the range: penalize proportional to how far outside, in units of range_width
    if value < min_v:
        overshoot = (min_v - value) / range_width
    else:
        overshoot = (value - max_v) / range_width

    score = 60 - (overshoot * 60)
    return max(0, min(score, 60))


def calculate_health(species: str, water_level: float, sunlight: float,
                      temperature: float, humidity: float, fertilizer: float) -> dict:
    """
    Calculate overall health score and per-factor breakdown for a plant.

    Returns a dict with:
        - overall_score (0-100)
        - status ("Healthy" / "Moderate" / "Critical" / "Dead")
        - factor_scores (dict of individual scores, useful for recommendations)
    """
    info = get_species_info(species)

    water_range = info["water_requirement"]
    sun_range = info["sunlight_requirement"]
    temp_range = info["temperature_range"]
    hum_range = info["humidity_range"]
    fert_ideal = info["fertilizer_ideal"]

    factor_scores = {
        "water": _score_against_range(water_level, water_range["min"], water_range["max"], water_range["ideal"]),
        "sunlight": _score_against_range(sunlight, sun_range["min"], sun_range["max"], sun_range["ideal"]),
        "temperature": _score_against_range(temperature, temp_range["min"], temp_range["max"], temp_range["ideal"]),
        "humidity": _score_against_range(humidity, hum_range["min"], hum_range["max"], hum_range["ideal"]),
        # Fertilizer has no strict min/max in our data, so treat ideal +/-30 as the range
        "fertilizer": _score_against_range(fertilizer, max(fert_ideal - 30, 0), fert_ideal + 30, fert_ideal),
    }

    overall_score = sum(factor_scores[f] * FACTOR_WEIGHTS[f] for f in FACTOR_WEIGHTS)
    overall_score = round(max(0, min(overall_score, 100)), 1)

    if water_level <= 2:
        # Severe water deprivation overrides everything else — plants die without water
        overall_score = min(overall_score, 15)

    if overall_score >= 75:
        status = "Healthy"
    elif overall_score >= 50:
        status = "Moderate"
    elif overall_score > 15:
        status = "Critical"
    else:
        status = "Dead"

    return {
        "overall_score": overall_score,
        "status": status,
        "factor_scores": {k: round(v, 1) for k, v in factor_scores.items()},
    }
