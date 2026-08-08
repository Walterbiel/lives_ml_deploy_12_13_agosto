from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel


model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    model = joblib.load("heart_disease_pipeline.pkl")
    yield


app = FastAPI(
    title="Heart Disease API",
    lifespan=lifespan
)


class HeartDiseaseInput(BaseModel):
    age: int
    sex: str
    resting_bp_systolic: int
    resting_bp_diastolic: int
    cholesterol_total: int
    hdl: int
    ldl: int
    triglycerides: int
    fasting_blood_sugar: int
    hba1c: float
    bmi: float
    resting_heart_rate: int
    max_heart_rate_achieved: int
    chest_pain_type: str
    exercise_induced_angina: bool
    st_depression: float
    family_history: bool
    smoker_status: str
    alcohol_units_per_week: float
    exercise_minutes_per_week: int
    sleep_hours: float
    stress_score: float
    wearable_owner: bool
    daily_steps: int
    diet_quality_score: float


@app.get("/")
def root():
    return {
        "status": "API funcionando"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/predict")
def predict(data: HeartDiseaseInput):

    input_data = pd.DataFrame([
        data.model_dump()
    ])

    prediction = model.predict(input_data)[0]

    probability = model.predict_proba(input_data)[0][1]

    return {
        "prediction": int(prediction),
        "probability": float(probability)
    }