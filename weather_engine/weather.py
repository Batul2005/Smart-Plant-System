"""
weather.py
----------
Simple Markov-chain weather simulator. Weather doesn't change uniformly at
random in real life — sunny days are more likely to be followed by sunny
days, storms are rare and short-lived. This module encodes that with a
basic transition matrix instead of pure uniform randomness, which makes
the simulation feel more realistic.
"""

import random

WEATHER_TYPES = ["Sunny", "Cloudy", "Rainy", "Stormy"]

# Transition probabilities: given current weather, P(next weather)
TRANSITION_MATRIX = {
    "Sunny":  {"Sunny": 0.55, "Cloudy": 0.30, "Rainy": 0.10, "Stormy": 0.05},
    "Cloudy": {"Sunny": 0.35, "Cloudy": 0.35, "Rainy": 0.22, "Stormy": 0.08},
    "Rainy":  {"Sunny": 0.20, "Cloudy": 0.30, "Rainy": 0.40, "Stormy": 0.10},
    "Stormy": {"Sunny": 0.15, "Cloudy": 0.35, "Rainy": 0.35, "Stormy": 0.15},
}

# Effect of each weather type on environmental deltas per simulation cycle.
# Values are added directly to the relevant sensor reading.
WEATHER_EFFECTS = {
    "Sunny":  {"water_level": -8, "sunlight": +15, "humidity": -5},
    "Cloudy": {"water_level": -3, "sunlight": -10, "humidity": +2},
    "Rainy":  {"water_level": +20, "sunlight": -25, "humidity": +15},
    "Stormy": {"water_level": +15, "sunlight": -35, "humidity": +20},
}


def next_weather(current_weather: str = None) -> str:
    """
    Return the next weather state given the current one, using the
    transition matrix. If no current weather is supplied (e.g. first
    cycle ever), pick uniformly at random.
    """
    if current_weather not in TRANSITION_MATRIX:
        return random.choice(WEATHER_TYPES)

    probabilities = TRANSITION_MATRIX[current_weather]
    outcomes = list(probabilities.keys())
    weights = list(probabilities.values())
    return random.choices(outcomes, weights=weights, k=1)[0]


def get_weather_effect(weather: str) -> dict:
    """Return the environmental delta dict for a given weather type."""
    return WEATHER_EFFECTS.get(weather, {"water_level": 0, "sunlight": 0, "humidity": 0})
