"""
generate_dataset.py
--------------------
Generates a synthetic but physiologically grounded training dataset for
the ML model.

Why synthetic data, stated honestly:
Real IoT sensor logs paired with verified plant-health outcomes over
months don't exist for this project. Rather than inventing arbitrary
numbers, this generator:
  1. Samples realistic environmental conditions per species (uniform
     across plausible operating ranges, including both ideal and
     stressed conditions).
  2. Uses the SAME health_engine.calculate_health() function the live
     app uses as the ground-truth health label (so the ML model is
     learning the actual domain logic, not noise).
  3. Adds Gaussian sensor noise + label noise to simulate real-world
     measurement imperfection, so the model has to generalize rather
     than memorize a deterministic formula.
  4. Derives growth_rate and days_to_flowering from health score with
     realistic variance, since faster/slower growth correlates with
     health but is never perfectly deterministic in real plants.

This produces a dataset large enough (15,000 rows) for Random Forest /
XGBoost to learn meaningful patterns, and is fully reproducible.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from backend.plant_species import PLANT_SPECIES
from backend.health_engine import calculate_health

RANDOM_SEED = 42
N_SAMPLES_PER_SPECIES = 3000


def generate_dataset(output_path: str):
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []

    for species, info in PLANT_SPECIES.items():
        w = info["water_requirement"]
        s = info["sunlight_requirement"]
        t = info["temperature_range"]
        h = info["humidity_range"]
        fert_ideal = info["fertilizer_ideal"]
        growth_speed = info["growth_speed"]

        for _ in range(N_SAMPLES_PER_SPECIES):
            # Sample across a WIDER range than the ideal band so the model
            # sees both healthy and stressed examples (0 to 1.4x the species' max).
            water_level = rng.uniform(0, max(w["max"] * 1.4, 100))
            sunlight = rng.uniform(0, 100)
            temperature = rng.uniform(max(t["min"] - 10, 0), t["max"] + 10)
            humidity = rng.uniform(0, 100)
            fertilizer = rng.uniform(0, 100)

            # Ground truth health via the same engine the live app uses
            health = calculate_health(
                species=species,
                water_level=water_level,
                sunlight=sunlight,
                temperature=temperature,
                humidity=humidity,
                fertilizer=fertilizer,
            )
            true_score = health["overall_score"]

            # Add label noise: real plant health has measurement/observation
            # error and biological variance even under identical conditions.
            noisy_score = np.clip(true_score + rng.normal(0, 4), 0, 100)

            # Growth rate (% of stage progress per day) correlates with health
            # and species growth_speed, with realistic biological variance.
            base_growth_rate = (noisy_score / 100) * growth_speed * 2.5
            growth_rate = max(0, base_growth_rate + rng.normal(0, 0.3))

            # Days to flowering: healthier + faster-growing species flower sooner.
            # Unhealthy plants (low score) may never flower (we cap with a
            # large number representing "not on track").
            if noisy_score < 30:
                days_to_flowering = rng.uniform(60, 120)  # effectively stalled
            else:
                base_days = 40 / max(growth_speed, 0.1)
                days_to_flowering = base_days * (1.3 - noisy_score / 100) + rng.normal(0, 3)
                days_to_flowering = max(5, days_to_flowering)

            rows.append({
                "species": species,
                "water_level": round(water_level, 2),
                "sunlight": round(sunlight, 2),
                "temperature": round(temperature, 2),
                "humidity": round(humidity, 2),
                "fertilizer": round(fertilizer, 2),
                "health_score": round(noisy_score, 2),
                "growth_rate": round(growth_rate, 3),
                "days_to_flowering": round(days_to_flowering, 1),
            })

    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)  # shuffle
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} rows -> {output_path}")
    print(df.describe(include="all"))
    return df


if __name__ == "__main__":
    out_path = os.path.join(os.path.dirname(__file__), "dataset.csv")
    generate_dataset(out_path)
