-- schema.sql

CREATE TABLE consumer_shopping_input (
    customer_id                  TEXT PRIMARY KEY,
    batch_id                     TEXT,
    age                          INTEGER,
    monthly_income               INTEGER,
    daily_internet_hours         REAL,
    smartphone_usage_years       INTEGER,
    social_media_hours           REAL,
    online_payment_trust_score   INTEGER,
    tech_savvy_score             INTEGER,
    monthly_online_orders        INTEGER,
    monthly_store_visits         INTEGER,
    avg_online_spend             INTEGER,
    avg_store_spend              INTEGER,
    discount_sensitivity         INTEGER,
    return_frequency             INTEGER,
    avg_delivery_days            INTEGER,
    delivery_fee_sensitivity     INTEGER,
    free_return_importance       INTEGER,
    product_availability_online  INTEGER,
    impulse_buying_score         INTEGER,
    need_touch_feel_score        INTEGER,
    brand_loyalty_score          INTEGER,
    environmental_awareness      INTEGER,
    time_pressure_level          INTEGER,
    gender                       TEXT,
    city_tier                    TEXT
);

CREATE TABLE shopping_preference_predictions (
    customer_id         TEXT PRIMARY KEY,
    batch_id            TEXT,
    prediction          INTEGER,
    label               TEXT,
    probability_online  REAL,
    scored_at           TIMESTAMP DEFAULT NOW()
);