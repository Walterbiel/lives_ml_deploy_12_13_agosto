# generate_data.py

import uuid
from datetime import datetime
from dotenv import load_dotenv
import os

import numpy as np
import pandas as pd

N = 500
rng = np.random.default_rng()

df = pd.DataFrame({
    "customer_id": [str(uuid.uuid4()) for _ in range(N)],
    "batch_id": datetime.now().strftime("batch_%Y%m%d_%H%M%S"),
    "age": rng.integers(18, 80, N),
    "monthly_income": rng.integers(15005, 249990, N),
    "daily_internet_hours": rng.normal(6.0, 2.0, N).clip(1, 12).round(1),
    "smartphone_usage_years": rng.integers(1, 15, N),
    "social_media_hours": rng.normal(2.5, 1.3, N).clip(0, 6).round(1),
    "online_payment_trust_score": rng.integers(1, 11, N),
    "tech_savvy_score": rng.integers(1, 11, N),
    "monthly_online_orders": rng.integers(0, 50, N),
    "monthly_store_visits": rng.integers(0, 20, N),
    "avg_online_spend": rng.integers(523, 149997, N),
    "avg_store_spend": rng.integers(542, 149973, N),
    "discount_sensitivity": rng.integers(1, 11, N),
    "return_frequency": rng.integers(0, 10, N),
    "avg_delivery_days": rng.integers(1, 8, N),
    "delivery_fee_sensitivity": rng.integers(1, 11, N),
    "free_return_importance": rng.integers(1, 11, N),
    "product_availability_online": rng.integers(1, 11, N),
    "impulse_buying_score": rng.integers(1, 11, N),
    "need_touch_feel_score": rng.integers(1, 11, N),
    "brand_loyalty_score": rng.integers(1, 11, N),
    "environmental_awareness": rng.integers(1, 11, N),
    "time_pressure_level": rng.integers(1, 11, N),
    "gender": rng.choice(["Female", "Male", "Other"], N),
    "city_tier": rng.choice(["Tier 1", "Tier 2", "Tier 3"], N),
})

load_dotenv()

(
    spark.createDataFrame(df).write
    .format("postgresql")
    .option("host", os.getenv("DB_HOST"))
    .option("port", os.getenv("DB_PORT"))
    .option("database", os.getenv("DB_NAME"))
    .option("dbtable", os.getenv("INPUT_TABLE"))
    .option("user", os.getenv("DB_USER"))
    .option("password", os.getenv("DB_PASSWORD"))
    .mode("append")
    .save()
)

print(f"{len(df)} registros inseridos. Lote: {df['batch_id'][0]}")