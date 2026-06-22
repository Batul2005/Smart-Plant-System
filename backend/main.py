"""
main.py
-------
FastAPI application entrypoint. Run with:
    uvicorn backend.main:app --reload --port 8000

Note: The Streamlit dashboard (frontend/dashboard.py) talks directly to
the backend/* modules rather than going over HTTP — this avoids needing
two processes running for the demo. This FastAPI app is provided as a
genuine, separately-runnable REST API (useful for integrating with other
clients, mobile apps, Postman testing, etc.) per the project spec's
API Endpoints section.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import init_db
from backend.routes import router

app = FastAPI(
    title="Smart Digital Plant Monitoring System",
    description="API for managing virtual plant digital twins, health prediction, "
                "and disease detection.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {
        "message": "Smart Digital Plant Monitoring System API",
        "docs": "/docs",
    }
