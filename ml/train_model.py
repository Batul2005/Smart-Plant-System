"""
train_model.py
---------------
Trains the ML prediction models used by the dashboard:

  1. health_score model      (RandomForestRegressor)
  2. growth_rate model       (RandomForestRegressor)
  3. days_to_flowering model (RandomForestRegressor)

All three share the same feature set: [species (one-hot), water_level,
sunlight, temperature, humidity, fertilizer].

Why three separate models instead of one multi-output model: each target
has a different noise profile and feature sensitivity (e.g. days_to_flowering
is dominated by health_score + growth_speed in a nonlinear way), and
scikit-learn's RandomForestRegressor handles multi-output natively but
single-output models give cleaner per-target evaluation metrics, which
matters for an honest report of model quality.

Run this after generate_dataset.py. Saves models + the fitted
species encoder to ml/models/ as .joblib files.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

DATA_PATH = os.path.join(os.path.dirname(__file__), "dataset.csv")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

FEATURE_COLS = ["species", "water_level", "sunlight", "temperature", "humidity", "fertilizer"]
TARGETS = ["health_score", "growth_rate", "days_to_flowering"]


def build_pipeline() -> Pipeline:
    """
    Build a preprocessing + RandomForest pipeline. One-hot encodes the
    categorical `species` column and passes numeric features through.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ("species_ohe", OneHotEncoder(handle_unknown="ignore"), ["species"]),
        ],
        remainder="passthrough",
    )

    model = RandomForestRegressor(
        n_estimators=80,
        max_depth=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )

    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def train_all_models():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. Run generate_dataset.py first."
        )

    df = pd.read_csv(DATA_PATH)
    os.makedirs(MODEL_DIR, exist_ok=True)

    X = df[FEATURE_COLS]
    metrics = {}

    for target in TARGETS:
        y = df[target]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        pipeline = build_pipeline()
        pipeline.fit(X_train, y_train)

        preds = pipeline.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        r2 = r2_score(y_test, preds)
        metrics[target] = {"MAE": round(mae, 3), "R2": round(r2, 4)}

        model_path = os.path.join(MODEL_DIR, f"{target}_model.joblib")
        joblib.dump(pipeline, model_path, compress=3)
        print(f"[{target}] MAE={mae:.3f}  R2={r2:.4f}  -> saved to {model_path}")

    metrics_path = os.path.join(MODEL_DIR, "metrics.joblib")
    joblib.dump(metrics, metrics_path)
    print(f"\nAll models trained. Metrics saved to {metrics_path}")
    return metrics


if __name__ == "__main__":
    train_all_models()
