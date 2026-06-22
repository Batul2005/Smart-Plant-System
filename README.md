# 🌿 Smart Digital Plant Monitoring System

A full-stack **digital twin** for houseplants — simulates real environmental conditions, calculates plant health using domain-grounded rules, predicts growth outcomes with a trained machine learning model, screens leaf photos for visible stress/disease using computer vision, and ties it all together in an interactive Streamlit dashboard.

Built as a portfolio project demonstrating practical full-stack + ML + CV engineering — every number you see in this app is computed by real, working code (no mocked data, no placeholder model files).

---

## ✨ What it actually does

| Module | What's real about it |
|---|---|
| **Health Engine** | Deterministic, explainable scoring (0–100) based on each species' real horticultural water/light/temp/humidity ranges — not arbitrary thresholds |
| **Weather Engine** | A Markov chain (not uniform random) — sunny days are more likely to stay sunny, storms are rare, matching real weather persistence |
| **Simulation** | Each "cycle" applies weather effects + natural resource decay, recalculates health, and probabilistically advances growth stage — a genuine time-step digital twin |
| **ML Prediction** | 3 `RandomForestRegressor` models (scikit-learn) trained on 15,000 samples, with real measured accuracy (R² / MAE) shown in-app, not hidden |
| **Disease Detection** | Real OpenCV HSV color analysis + Laplacian texture variance — calibrated and tested against synthetic leaf images, not a fake pretrained YOLO weights file |
| **Notifications** | Logged to SQLite + best-effort desktop notification via `plyer` |
| **Auth** | SHA-256 password hashing (see note below on why not bcrypt) |

### An honest note on what's *not* "real-world data"

This project runs entirely on your laptop with no IoT hardware and no public plant-disease dataset attached. Two places where that matters, stated plainly rather than glossed over:

1. **ML training data is synthetic.** There's no months-long log of real soil sensors paired with verified outcomes available for this project. Instead, `ml/generate_dataset.py` samples realistic environmental ranges per species and labels them using the **same health-scoring logic the live app uses**, plus Gaussian noise — so the model learns genuine domain relationships rather than random numbers. This is a standard, legitimate technique (simulation-based training data) when real sensor logs aren't available, and it's documented in the code rather than disguised.
2. **Disease detection is classical CV, not deep learning.** A real YOLOv8 disease classifier needs thousands of labeled diseased-leaf photos to train. Shipping a `.pt` weights file that was never actually trained on plant disease data would just be a randomly-initialized model producing meaningless output dressed up as AI — which is worse than not having the feature at all. Instead, `disease_detection/detect.py` does genuine, calibrated HSV color-ratio and texture-variance analysis, a real first-pass technique used in agricultural CV. The module is structured so a trained YOLOv8 model can be dropped in later (see `detect_with_yolo_placeholder()`).

---

## 🏗️ Architecture

```
Smart_Plant_System/
│
├── app.py                      # Streamlit entrypoint (login/register)
├── pages/                      # Streamlit multi-page app (required location)
│   ├── 1_My_Plants.py
│   ├── 2_Dashboard.py
│   ├── 3_AI_Prediction.py
│   ├── 4_Disease_Scan.py
│   └── 5_Notifications.py
├── frontend/pages/              # Mirror copy matching the original spec's folder layout
│
├── backend/
│   ├── main.py                 # FastAPI app (standalone REST API, runs independently)
│   ├── routes.py                # All API endpoints
│   ├── schemas.py               # Pydantic request/response models
│   ├── models.py                # Data access layer (DB reads/writes)
│   ├── health_engine.py         # Health scoring logic
│   ├── simulation.py            # Time-step digital twin engine
│   └── plant_species.py         # Reference horticultural data
│
├── database/
│   ├── database.py               # SQLite connection + schema
│   └── plant_system.db          # Created on first run
│
├── ml/
│   ├── generate_dataset.py      # Synthetic dataset generator
│   ├── train_model.py           # Trains & evaluates Random Forest models
│   ├── predict.py               # Loads models, serves predictions
│   ├── dataset.csv              # Generated training data (15,000 rows)
│   └── models/                  # Saved .joblib model files + metrics
│
├── disease_detection/
│   └── detect.py                # OpenCV leaf analysis
│
├── weather_engine/
│   └── weather.py                # Markov-chain weather simulator
│
├── utils/
│   ├── recommendation.py        # Rule-based AI advisory engine
│   └── notification.py          # Alerts (DB + desktop + email stub)
│
└── requirements.txt
```

**Why a separate FastAPI backend AND a Streamlit app talking directly to `backend/*`?**
The Streamlit dashboard imports backend modules directly (no HTTP hop) so the whole demo runs as a single process — simpler for local development and grading. The FastAPI app (`backend/main.py`) is a fully working, separately-runnable REST API implementing every endpoint in the original spec, useful if you want to integrate with Postman, a mobile app, or a different frontend later.

---

## 🚀 Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Generate training data & train the ML models (one-time)
```bash
python ml/generate_dataset.py
python ml/train_model.py
```
This creates `ml/dataset.csv` (15,000 rows) and saves trained models to `ml/models/`. You'll see real accuracy metrics printed, e.g.:
```
[health_score] MAE=5.838  R2=0.7722
[growth_rate] MAE=0.258  R2=0.7188
[days_to_flowering] MAE=9.935  R2=0.8020
```

### 3. Run the Streamlit dashboard (main app)
```bash
streamlit run app.py
```
Open the URL it prints (usually `http://localhost:8501`), register an account, and add a plant.

### 4. (Optional) Run the FastAPI backend separately
```bash
uvicorn backend.main:app --reload --port 8000
```
Interactive API docs at `http://localhost:8000/docs`.

---

## 🧪 How to demo it

1. **Register** → create an account (runs entirely locally, nothing leaves your machine).
2. **Add a plant** → pick a species (Rose, Sunflower, Cactus, Tulsi, Aloe Vera).
3. **Dashboard** → click "Advance 1 day" a few times to watch weather, water, and health evolve. Try "Water the plant" to see the health gauge respond.
4. **AI Prediction** → see the Random Forest's forecast, and play with the **What-if Simulator** sliders to see predictions update live.
5. **Disease Scan** → upload any leaf photo (or test with a photo of any green plant) to see the CV pipeline's diagnosis.
6. **Notifications** → after enough neglect (or by forcing bad conditions), see alerts populate.

---

## 📊 Database Schema

```sql
Users(user_id, name, email, password, created_at)
Plants(plant_id, user_id, plant_name, species, growth_stage, planted_date, is_alive)
SensorData(id, plant_id, moisture, water_level, sunlight, temperature, humidity, fertilizer, weather, recorded_at)
Predictions(id, plant_id, health_score, health_status, growth_rate, days_to_flowering, predicted_at)
Notifications(id, plant_id, message, severity, created_at, is_read)
DiseaseScans(id, plant_id, diagnosis, confidence, treatment, scanned_at)
```

## 🔌 API Endpoints (FastAPI)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/register` | Create a user account |
| POST | `/login` | Authenticate |
| POST | `/addPlant` | Add a plant |
| GET | `/plants?user_id=` | List a user's plants |
| DELETE | `/plants/{plant_id}` | Remove a plant |
| POST | `/sensorData` | Advance one simulation cycle |
| GET | `/health?plant_id=` | Current health + recommendations |
| GET | `/prediction?plant_id=` | ML-predicted health/growth/flowering |
| POST | `/uploadImage?plant_id=` | Upload a leaf photo for CV analysis |
| GET | `/dashboard?plant_id=` | Aggregate dashboard payload |
| GET | `/species` | List supported species |

---

## 🔐 Security notes (read before deploying anywhere public)

- Passwords are hashed with SHA-256 + no per-user salt — fine for a local portfolio demo, **not** production-grade. For production, switch to `bcrypt` or `argon2` (e.g. `passlib`).
- `email_alert()` in `utils/notification.py` requires the caller to supply SMTP credentials via environment variables — none are hardcoded.
- CORS is wide open (`allow_origins=["*"]`) in `backend/main.py` for local demo convenience — restrict this before any public deployment.

---

## 🧠 Tech Stack

**Frontend:** Streamlit, Plotly
**Backend:** FastAPI, Python 3
**Database:** SQLite
**ML:** scikit-learn (RandomForestRegressor)
**CV:** OpenCV (HSV color analysis, Laplacian texture variance)
**Notifications:** SQLite log + `plyer` desktop notifications + optional SMTP email

---

## 📈 Possible extensions (good talking points for an interview)

- Swap the synthetic ML dataset for real Arduino/Raspberry Pi soil-moisture + DHT22 sensor logs.
- Collect real labeled diseased-leaf photos (e.g. the public **PlantVillage** dataset) and train an actual YOLOv8 classifier to replace the classical CV module — the architecture already has a clear seam for this (`detect_with_yolo_placeholder()`).
- Move from SQLite to PostgreSQL/MongoDB Atlas for multi-device sync.
- Add bcrypt password hashing and JWT-based auth for the FastAPI layer.
- Deploy the Streamlit app to Streamlit Community Cloud and the FastAPI backend to Render/Railway.
#   S m a r t - P l a n t - S y s t e m  
 