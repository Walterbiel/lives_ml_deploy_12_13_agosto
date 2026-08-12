# function_app.py

import azure.functions as func
import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

fast_app = FastAPI(title="Shopping Preference API", version="1.0.0")

modelo = joblib.load("shopping_preference_model.pkl")


class Cliente(BaseModel):
    age: int
    monthly_income: int
    daily_internet_hours: float
    smartphone_usage_years: int
    social_media_hours: float
    online_payment_trust_score: int
    tech_savvy_score: int
    monthly_online_orders: int
    monthly_store_visits: int
    avg_online_spend: int
    avg_store_spend: int
    discount_sensitivity: int
    return_frequency: int
    avg_delivery_days: int
    delivery_fee_sensitivity: int
    free_return_importance: int
    product_availability_online: int
    impulse_buying_score: int
    need_touch_feel_score: int
    brand_loyalty_score: int
    environmental_awareness: int
    time_pressure_level: int
    gender: str
    city_tier: str


@fast_app.get("/health")
def health():
    return {"status": "ok"}


@fast_app.post("/predict")
def predict(cliente: Cliente):
    df = pd.DataFrame([cliente.model_dump()])

    prediction = int(modelo.predict(df)[0])
    probability = float(modelo.predict_proba(df)[0][1])

    return {
        "prediction": prediction,
        "label": "Online" if prediction == 1 else "Store",
        "probability_online": probability,
    }


app = func.AsgiFunctionApp(app=fast_app, http_auth_level=func.AuthLevel.ANONYMOUS)
