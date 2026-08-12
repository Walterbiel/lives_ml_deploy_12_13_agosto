# inference.py
#!pip install lightgbm==4.6.0


import os

import joblib
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

OPTIONS = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

COLUNAS = [
    "age", "monthly_income", "daily_internet_hours", "smartphone_usage_years",
    "social_media_hours", "online_payment_trust_score", "tech_savvy_score",
    "monthly_online_orders", "monthly_store_visits", "avg_online_spend",
    "avg_store_spend", "discount_sensitivity", "return_frequency",
    "avg_delivery_days", "delivery_fee_sensitivity", "free_return_importance",
    "product_availability_online", "impulse_buying_score", "need_touch_feel_score",
    "brand_loyalty_score", "environmental_awareness", "time_pressure_level",
    "gender", "city_tier",
]

QUERY = f"""(
    SELECT i.*
    FROM {os.getenv("INPUT_TABLE")} i
    LEFT JOIN {os.getenv("OUTPUT_TABLE")} p
           ON p.customer_id = i.customer_id
    WHERE p.customer_id IS NULL
) AS pendentes"""

df = (
    spark.read.format("postgresql")
    .options(**OPTIONS)
    .option("dbtable", QUERY)
    .load()
    .toPandas()
)

if df.empty:
    print("Nada pendente para pontuar.")
    dbutils.notebook.exit("ok")

modelo = joblib.load("shopping_preference_model.pkl")

X = df[COLUNAS]

resultado = pd.DataFrame({
    "customer_id": df["customer_id"],
    "batch_id": df["batch_id"],
    "prediction": modelo.predict(X),
    "probability_online": modelo.predict_proba(X)[:, 1],
})
resultado["label"] = resultado["prediction"].map({0: "Store", 1: "Online"})

(
    spark.createDataFrame(resultado).write.format("postgresql")
    .options(**OPTIONS)
    .option("dbtable", os.getenv("OUTPUT_TABLE"))
    .mode("append")
    .save()
)

print(f"{len(resultado)} predições salvas")
print(resultado["label"].value_counts().to_dict())