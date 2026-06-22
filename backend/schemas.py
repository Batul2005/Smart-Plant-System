"""
schemas.py
----------
Pydantic models defining the request/response contracts for the FastAPI
backend. Keeping these separate from models.py (DB access) follows clean
architecture: schemas = API boundary, models = persistence layer.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PlantCreate(BaseModel):
    user_id: int
    plant_name: str = Field(..., min_length=1, max_length=100)
    species: str


class SensorDataIn(BaseModel):
    plant_id: int
    moisture: Optional[float] = None
    water_level: Optional[float] = None
    sunlight: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    fertilizer: Optional[float] = None
