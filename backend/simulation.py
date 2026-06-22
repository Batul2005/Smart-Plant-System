"""
simulation.py
--------------
The core time-step simulation. Each "cycle" represents a unit of time
(e.g. one day). On each cycle:
  1. Weather advances (Markov chain).
  2. Weather affects water/sunlight/humidity.
  3. Natural decay is applied (water evaporates, nutrients deplete).
  4. Health score is recalculated.
  5. Growth stage may advance if health has been good.
  6. Sensor reading + prediction are logged to the database.
  7. Notifications are fired if thresholds are breached.

This module is the "digital twin" engine — it's what lets the dashboard
show a plant evolving over time without needing real IoT hardware, while
keeping every formula transparent and explainable.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random

from backend.plant_species import get_species_info, GROWTH_STAGES, STAGE_THRESHOLDS
from backend.health_engine import calculate_health
from weather_engine.weather import next_weather, get_weather_effect
from database.database import get_connection, now_iso
from utils.notification import check_and_notify

# Natural decay per cycle (independent of weather) — plants always use
# some water and nutrients just by being alive.
NATURAL_DECAY = {
    "water_level": -4,
    "fertilizer": -2,
}


def _clamp(value, lo=0, hi=100):
    return max(lo, min(hi, value))


def get_latest_sensor_reading(plant_id: int) -> dict:
    """Fetch the most recent sensor row for a plant, or sensible defaults if none exist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM SensorData WHERE plant_id = ? ORDER BY recorded_at DESC LIMIT 1",
            (plant_id,),
        ).fetchone()
    if row:
        return dict(row)
    return {
        "moisture": 50, "water_level": 60, "sunlight": 70,
        "temperature": 24, "humidity": 50, "fertilizer": 50, "weather": None,
    }


def run_cycle(plant_id: int, manual_overrides: dict = None) -> dict:
    """
    Advance one simulation cycle for a given plant.

    manual_overrides: optional dict to let a user manually set values
    (e.g. simulate "I watered the plant") before decay/weather is applied,
    mimicking real sensor input from a manual care action.

    Returns a dict with the new sensor state, health result, and any
    notifications fired.
    """
    manual_overrides = manual_overrides or {}

    with get_connection() as conn:
        plant = conn.execute(
            "SELECT * FROM Plants WHERE plant_id = ?", (plant_id,)
        ).fetchone()
    if plant is None:
        raise ValueError(f"No plant with id {plant_id}")
    plant = dict(plant)

    if not plant["is_alive"]:
        raise ValueError("Cannot simulate a dead plant. Add a new plant instead.")

    species_info = get_species_info(plant["species"])
    last = get_latest_sensor_reading(plant_id)

    # Step 1: advance weather
    weather = next_weather(last.get("weather"))
    effect = get_weather_effect(weather)

    # Step 2: apply manual overrides first (e.g. user just watered the plant)
    water_level = manual_overrides.get("water_level", last["water_level"])
    sunlight = manual_overrides.get("sunlight", last["sunlight"])
    temperature = manual_overrides.get("temperature", last["temperature"])
    humidity = manual_overrides.get("humidity", last["humidity"])
    fertilizer = manual_overrides.get("fertilizer", last["fertilizer"])
    moisture = manual_overrides.get("moisture", last.get("moisture", 50))

    # Step 3: apply weather effects + natural decay
    water_level = _clamp(water_level + effect["water_level"] + NATURAL_DECAY["water_level"])
    sunlight = _clamp(sunlight + effect["sunlight"])
    humidity = _clamp(humidity + effect["humidity"])
    fertilizer = _clamp(fertilizer + NATURAL_DECAY["fertilizer"])
    moisture = _clamp(water_level + random.uniform(-5, 5))

    # Temperature drifts slightly with weather (sunny=warmer, rainy=cooler) + small noise
    temp_drift = {"Sunny": 1.5, "Cloudy": 0, "Rainy": -1.5, "Stormy": -3}.get(weather, 0)
    temperature = round(_clamp(temperature + temp_drift + random.uniform(-1, 1), 0, 50), 1)

    # Step 4: calculate health
    health = calculate_health(
        species=plant["species"],
        water_level=water_level,
        sunlight=sunlight,
        temperature=temperature,
        humidity=humidity,
        fertilizer=fertilizer,
    )

    # Step 5: growth stage progression
    new_stage = _advance_growth_stage(plant["growth_stage"], health["overall_score"], health["status"])

    is_alive = 1
    if new_stage == "Dead Plant" or health["status"] == "Dead":
        is_alive = 0
        new_stage = "Dead Plant"

    # Step 6: persist sensor reading
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO SensorData (plant_id, moisture, water_level, sunlight, temperature, "
            "humidity, fertilizer, weather, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (plant_id, round(moisture, 1), round(water_level, 1), round(sunlight, 1),
             temperature, round(humidity, 1), round(fertilizer, 1), weather, now_iso()),
        )
        conn.execute(
            "UPDATE Plants SET growth_stage = ?, is_alive = ? WHERE plant_id = ?",
            (new_stage, is_alive, plant_id),
        )

    # Step 7: notifications
    alerts = check_and_notify(
        plant_id, plant["plant_name"], water_level, temperature,
        health["overall_score"], health["status"]
    )

    return {
        "plant_id": plant_id,
        "weather": weather,
        "water_level": round(water_level, 1),
        "sunlight": round(sunlight, 1),
        "temperature": temperature,
        "humidity": round(humidity, 1),
        "fertilizer": round(fertilizer, 1),
        "moisture": round(moisture, 1),
        "health": health,
        "growth_stage": new_stage,
        "is_alive": bool(is_alive),
        "alerts": alerts,
    }


def _advance_growth_stage(current_stage: str, health_score: float, status: str) -> str:
    """
    Decide whether the plant advances to the next growth stage.

    Logic: a plant only progresses if health has been Healthy/Moderate
    (i.e. not currently Critical/Dead), with a probability proportional
    to health score. This means a stressed plant can stay alive but stall
    in its current stage — same as in real horticulture.
    """
    if current_stage == "Dead Plant":
        return "Dead Plant"

    if status == "Dead":
        return "Dead Plant"

    if status == "Critical":
        return current_stage  # too stressed to grow this cycle

    current_idx = GROWTH_STAGES.index(current_stage)
    if current_idx >= len(GROWTH_STAGES) - 2:  # already at Fruit Bearing (last non-dead stage)
        return current_stage

    # Probability of advancing scales with health score
    advance_chance = (health_score - 50) / 100  # 0 at score 50, 0.5 at score 100
    advance_chance = max(0, advance_chance)

    if random.random() < advance_chance:
        return GROWTH_STAGES[current_idx + 1]
    return current_stage
