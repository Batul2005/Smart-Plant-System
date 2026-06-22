"""
models.py
---------
Data access layer: functions that read/write the database for Users,
Plants, SensorData, and Predictions. Both the FastAPI routes and the
Streamlit dashboard call into this module, so business logic for
"how do I create a plant" lives in exactly one place.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import get_connection, now_iso, hash_password


# ---------- Users ----------

def create_user(name: str, email: str, password: str) -> dict:
    with get_connection() as conn:
        existing = conn.execute("SELECT user_id FROM Users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise ValueError("An account with this email already exists.")
        cur = conn.execute(
            "INSERT INTO Users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
            (name, email, hash_password(password), now_iso()),
        )
        row = conn.execute("SELECT * FROM Users WHERE user_id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def authenticate_user(email: str, password: str) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Users WHERE email = ?", (email,)).fetchone()
    if row is None or row["password"] != hash_password(password):
        raise ValueError("Invalid email or password.")
    return dict(row)


def get_user_by_id(user_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# ---------- Plants ----------

def add_plant(user_id: int, plant_name: str, species: str) -> dict:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO Plants (user_id, plant_name, species, growth_stage, planted_date, is_alive) "
            "VALUES (?, ?, ?, 'Seed', ?, 1)",
            (user_id, plant_name, species, now_iso()),
        )
        plant_id = cur.lastrowid
        # Seed an initial sensor reading at species-ideal conditions so the
        # plant starts healthy rather than at undefined zero values.
        from backend.plant_species import get_species_info
        info = get_species_info(species)
        conn.execute(
            "INSERT INTO SensorData (plant_id, moisture, water_level, sunlight, temperature, "
            "humidity, fertilizer, weather, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (plant_id, info["water_requirement"]["ideal"], info["water_requirement"]["ideal"],
             info["sunlight_requirement"]["ideal"], info["temperature_range"]["ideal"],
             info["humidity_range"]["ideal"], info["fertilizer_ideal"], "Sunny", now_iso()),
        )
        row = conn.execute("SELECT * FROM Plants WHERE plant_id = ?", (plant_id,)).fetchone()
        return dict(row)


def delete_plant(plant_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM Plants WHERE plant_id = ?", (plant_id,))


def update_plant(plant_id: int, plant_name: str = None, species: str = None):
    with get_connection() as conn:
        if plant_name is not None:
            conn.execute("UPDATE Plants SET plant_name = ? WHERE plant_id = ?", (plant_name, plant_id))
        if species is not None:
            conn.execute("UPDATE Plants SET species = ? WHERE plant_id = ?", (species, plant_id))


def get_plants_for_user(user_id: int) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Plants WHERE user_id = ? ORDER BY planted_date DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_plant_by_id(plant_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Plants WHERE plant_id = ?", (plant_id,)).fetchone()
    return dict(row) if row else None


# ---------- Sensor history / predictions ----------

def get_sensor_history(plant_id: int, limit: int = 100) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM SensorData WHERE plant_id = ? ORDER BY recorded_at ASC LIMIT ?",
            (plant_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def store_prediction(plant_id: int, health_score: float, health_status: str,
                      growth_rate: float, days_to_flowering: float):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO Predictions (plant_id, health_score, health_status, growth_rate, "
            "days_to_flowering, predicted_at) VALUES (?, ?, ?, ?, ?, ?)",
            (plant_id, health_score, health_status, growth_rate, days_to_flowering, now_iso()),
        )


def get_prediction_history(plant_id: int, limit: int = 100) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Predictions WHERE plant_id = ? ORDER BY predicted_at ASC LIMIT ?",
            (plant_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def store_disease_scan(plant_id: int, diagnosis: str, confidence: float, treatment: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO DiseaseScans (plant_id, diagnosis, confidence, treatment, scanned_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (plant_id, diagnosis, confidence, treatment, now_iso()),
        )


def get_disease_scan_history(plant_id: int, limit: int = 20) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM DiseaseScans WHERE plant_id = ? ORDER BY scanned_at DESC LIMIT ?",
            (plant_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
