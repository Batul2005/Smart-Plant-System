"""
recommendation.py
------------------
Generates human-readable, actionable recommendations from a plant's
current sensor readings and health factor scores.

This is a rule-based expert system (the kind real agronomy advisory tools
use) rather than a generative model — recommendations need to be reliable,
specific, and auditable, not "creative."
"""

from backend.plant_species import get_species_info


def generate_recommendations(species: str, water_level: float, sunlight: float,
                              temperature: float, humidity: float, fertilizer: float,
                              factor_scores: dict) -> list:
    """
    Return a list of recommendation strings, ordered by urgency
    (most critical factor first).
    """
    info = get_species_info(species)
    recs = []

    water_range = info["water_requirement"]
    sun_range = info["sunlight_requirement"]
    temp_range = info["temperature_range"]
    hum_range = info["humidity_range"]

    # Sort factors by severity (lowest score = most urgent) so the most
    # important advice surfaces first.
    ordered_factors = sorted(factor_scores.items(), key=lambda kv: kv[1])

    for factor, score in ordered_factors:
        if score >= 75:
            continue  # this factor is fine, no advice needed

        if factor == "water":
            if water_level < water_range["min"]:
                recs.append(
                    f"💧 Water level is low ({water_level:.0f}%, needs {water_range['min']}-{water_range['max']}%). "
                    f"Water the plant soon."
                )
            elif water_level > water_range["max"]:
                recs.append(
                    f"💧 Soil is overwatered ({water_level:.0f}%, ideal max {water_range['max']}%). "
                    f"Hold off watering and check drainage."
                )

        elif factor == "sunlight":
            if sunlight < sun_range["min"]:
                recs.append(
                    f"☀️ Sunlight exposure is too low ({sunlight:.0f}%, needs {sun_range['min']}%+). "
                    f"Move to a brighter spot or trim nearby shade."
                )
            elif sunlight > sun_range["max"]:
                recs.append(
                    f"☀️ Sunlight may be excessive ({sunlight:.0f}%). Consider partial shade during peak hours."
                )

        elif factor == "temperature":
            if temperature < temp_range["min"]:
                recs.append(
                    f"🌡️ Temperature is too low ({temperature:.0f}°C, needs {temp_range['min']}-{temp_range['max']}°C). "
                    f"Move to a warmer location."
                )
            elif temperature > temp_range["max"]:
                recs.append(
                    f"🌡️ Temperature is too high ({temperature:.0f}°C, max {temp_range['max']}°C). "
                    f"Provide shade or move away from direct heat."
                )

        elif factor == "humidity":
            if humidity < hum_range["min"]:
                recs.append(
                    f"💨 Humidity is low ({humidity:.0f}%, needs {hum_range['min']}%+). "
                    f"Mist the leaves or use a humidity tray."
                )
            elif humidity > hum_range["max"]:
                recs.append(
                    f"💨 Humidity is high ({humidity:.0f}%, max {hum_range['max']}%). "
                    f"Improve airflow to prevent fungal growth."
                )

        elif factor == "fertilizer":
            if fertilizer < info["fertilizer_ideal"] - 20:
                recs.append("🌱 Nutrient levels are low. Add fertilizer in the next feeding cycle.")
            elif fertilizer > info["fertilizer_ideal"] + 40:
                recs.append("🌱 Fertilizer level is high — avoid feeding for now to prevent root burn.")

    if not recs:
        recs.append("✅ All environmental conditions are within ideal range. Keep up the routine!")

    return recs
