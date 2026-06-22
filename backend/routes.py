"""
routes.py
---------
FastAPI route definitions, grouped by resource. Kept separate from
main.py so the app factory stays clean and routes are independently
testable.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, UploadFile, File
import shutil
import tempfile

from backend.schemas import UserRegister, UserLogin, PlantCreate, SensorDataIn
from backend import models
from backend.health_engine import calculate_health
from backend.simulation import run_cycle, get_latest_sensor_reading
from backend.plant_species import get_species_list, get_species_info
from utils.recommendation import generate_recommendations
from ml.predict import predict_plant_outcomes, models_available
from disease_detection.detect import analyze_leaf_image

router = APIRouter()


# ---------- Auth ----------

@router.post("/register")
def register(payload: UserRegister):
    try:
        user = models.create_user(payload.name, payload.email, payload.password)
        user.pop("password", None)
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(payload: UserLogin):
    try:
        user = models.authenticate_user(payload.email, payload.password)
        user.pop("password", None)
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ---------- Plants ----------

@router.post("/addPlant")
def add_plant(payload: PlantCreate):
    if payload.species not in get_species_list():
        raise HTTPException(status_code=400, detail=f"Unsupported species: {payload.species}")
    plant = models.add_plant(payload.user_id, payload.plant_name, payload.species)
    return {"success": True, "plant": plant}


@router.get("/plants")
def get_plants(user_id: int):
    return {"plants": models.get_plants_for_user(user_id)}


@router.delete("/plants/{plant_id}")
def delete_plant(plant_id: int):
    models.delete_plant(plant_id)
    return {"success": True}


# ---------- Sensor data / simulation ----------

@router.post("/sensorData")
def submit_sensor_data(payload: SensorDataIn):
    """
    Advance one simulation cycle for the plant, optionally with manual
    sensor overrides (e.g. user just watered the plant).
    """
    overrides = {k: v for k, v in payload.dict().items() if k != "plant_id" and v is not None}
    try:
        result = run_cycle(payload.plant_id, manual_overrides=overrides)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/health")
def get_health(plant_id: int):
    plant = models.get_plant_by_id(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    reading = get_latest_sensor_reading(plant_id)
    health = calculate_health(
        species=plant["species"],
        water_level=reading["water_level"],
        sunlight=reading["sunlight"],
        temperature=reading["temperature"],
        humidity=reading["humidity"],
        fertilizer=reading["fertilizer"],
    )
    recs = generate_recommendations(
        plant["species"], reading["water_level"], reading["sunlight"],
        reading["temperature"], reading["humidity"], reading["fertilizer"],
        health["factor_scores"],
    )
    return {"health": health, "recommendations": recs, "current_reading": reading}


# ---------- ML Prediction ----------

@router.get("/prediction")
def get_prediction(plant_id: int):
    if not models_available():
        raise HTTPException(
            status_code=503,
            detail="ML models not trained yet. Run ml/generate_dataset.py then ml/train_model.py.",
        )
    plant = models.get_plant_by_id(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    reading = get_latest_sensor_reading(plant_id)
    prediction = predict_plant_outcomes(
        species=plant["species"],
        water_level=reading["water_level"],
        sunlight=reading["sunlight"],
        temperature=reading["temperature"],
        humidity=reading["humidity"],
        fertilizer=reading["fertilizer"],
    )
    models.store_prediction(
        plant_id,
        prediction["predicted_health_score"],
        "N/A",
        prediction["predicted_growth_rate"],
        prediction["predicted_days_to_flowering"],
    )
    return prediction


# ---------- Disease Detection ----------

@router.post("/uploadImage")
async def upload_image(plant_id: int, file: UploadFile = File(...)):
    plant = models.get_plant_by_id(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = analyze_leaf_image(tmp_path)
    finally:
        os.unlink(tmp_path)

    models.store_disease_scan(plant_id, result["diagnosis"], result["confidence"], result["treatment"])
    return result


# ---------- Dashboard aggregate ----------

@router.get("/dashboard")
def get_dashboard(plant_id: int):
    plant = models.get_plant_by_id(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    history = models.get_sensor_history(plant_id, limit=200)
    species_info = get_species_info(plant["species"])
    latest = get_latest_sensor_reading(plant_id)
    health = calculate_health(
        plant["species"], latest["water_level"], latest["sunlight"],
        latest["temperature"], latest["humidity"], latest["fertilizer"],
    )

    return {
        "plant": plant,
        "species_info": species_info,
        "current_reading": latest,
        "health": health,
        "history": history,
    }


@router.get("/species")
def list_species():
    return {"species": get_species_list()}
