"""
predict.py
----------
Loads the trained Random Forest models and exposes a single
`predict_plant_outcomes()` function used by both the FastAPI backend
and the Streamlit dashboard.

Models are loaded once at import time (lazy-cached) to avoid the cost of
re-reading .joblib files on every prediction call.
"""

import os
import joblib
import pandas as pd

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
TARGETS = ["health_score", "growth_rate", "days_to_flowering"]

_model_cache = {}


def _load_model(target: str):
    if target not in _model_cache:
        path = os.path.join(MODEL_DIR, f"{target}_model.joblib")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Model for '{target}' not found at {path}. "
                f"Run ml/generate_dataset.py then ml/train_model.py first."
            )
        _model_cache[target] = joblib.load(path)
    return _model_cache[target]


def models_available() -> bool:
    """Check whether all trained model files exist on disk."""
    return all(
        os.path.exists(os.path.join(MODEL_DIR, f"{t}_model.joblib"))
        for t in TARGETS
    )


def get_metrics() -> dict:
    """Load and return the saved evaluation metrics from training."""
    path = os.path.join(MODEL_DIR, "metrics.joblib")
    if not os.path.exists(path):
        return {}
    return joblib.load(path)


def predict_plant_outcomes(species: str, water_level: float, sunlight: float,
                            temperature: float, humidity: float, fertilizer: float) -> dict:
    """
    Run all three trained models on the given environmental readings.

    Returns:
        {
            "predicted_health_score": float,
            "predicted_growth_rate": float,   # % stage progress per day
            "predicted_days_to_flowering": float
        }
    """
    input_df = pd.DataFrame([{
        "species": species,
        "water_level": water_level,
        "sunlight": sunlight,
        "temperature": temperature,
        "humidity": humidity,
        "fertilizer": fertilizer,
    }])

    results = {}
    for target in TARGETS:
        model = _load_model(target)
        pred = model.predict(input_df)[0]
        results[f"predicted_{target}"] = round(float(pred), 2)

    # Clip health score prediction to valid 0-100 range
    results["predicted_health_score"] = max(0, min(100, results["predicted_health_score"]))
    results["predicted_growth_rate"] = max(0, results["predicted_growth_rate"])
    results["predicted_days_to_flowering"] = max(0, results["predicted_days_to_flowering"])

    return results
