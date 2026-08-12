# streamlit_app.py

import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "https://func-shopping-preference-wb-gaemh5bgdtgearaa.brazilsouth-01.azurewebsites.net") + "/predict"

st.set_page_config(page_title="Shopping Preference", layout="wide")
st.title("Shopping Preference")
st.write("Interface consumindo a API FastAPI com o modelo de Machine Learning")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Perfil")
    age = st.number_input("Idade", 18, 79, 45)
    monthly_income = st.number_input("Renda mensal", 15005, 249989, 130000)
    gender = st.selectbox("Gênero", ["Female", "Male", "Other"])
    city_tier = st.selectbox("Tier da cidade", ["Tier 1", "Tier 2", "Tier 3"])
    daily_internet_hours = st.slider("Horas de internet por dia", 1.0, 12.0, 6.0)
    social_media_hours = st.slider("Horas de redes sociais", 0.0, 6.0, 2.5)
    smartphone_usage_years = st.slider("Anos usando smartphone", 1, 14, 8)
    tech_savvy_score = st.slider("Afinidade com tecnologia", 1, 10, 6)

with col2:
    st.subheader("Consumo")
    avg_store_spend = st.number_input("Gasto médio em loja", 542, 149972, 75000)
    avg_online_spend = st.number_input("Gasto médio online", 523, 149996, 75000)
    monthly_online_orders = st.slider("Pedidos online por mês", 0, 49, 25)
    monthly_store_visits = st.slider("Visitas à loja por mês", 0, 19, 9)
    online_payment_trust_score = st.slider("Confiança em pagamento online", 1, 10, 5)
    discount_sensitivity = st.slider("Sensibilidade a desconto", 1, 10, 5)
    impulse_buying_score = st.slider("Compra por impulso", 1, 10, 5)
    brand_loyalty_score = st.slider("Fidelidade à marca", 1, 10, 6)

with col3:
    st.subheader("Preferências")
    need_touch_feel_score = st.slider("Necessidade de ver o produto", 1, 10, 5)
    product_availability_online = st.slider("Disponibilidade online", 1, 10, 6)
    avg_delivery_days = st.slider("Prazo médio de entrega", 1, 7, 4)
    delivery_fee_sensitivity = st.slider("Sensibilidade ao frete", 1, 10, 5)
    free_return_importance = st.slider("Importância da devolução grátis", 1, 10, 5)
    return_frequency = st.slider("Frequência de devolução", 0, 9, 5)
    environmental_awareness = st.slider("Consciência ambiental", 1, 10, 5)
    time_pressure_level = st.slider("Pressão de tempo", 1, 10, 6)

if st.button("Realizar previsão", type="primary"):
    payload = {
        "age": age,
        "monthly_income": monthly_income,
        "daily_internet_hours": daily_internet_hours,
        "smartphone_usage_years": smartphone_usage_years,
        "social_media_hours": social_media_hours,
        "online_payment_trust_score": online_payment_trust_score,
        "tech_savvy_score": tech_savvy_score,
        "monthly_online_orders": monthly_online_orders,
        "monthly_store_visits": monthly_store_visits,
        "avg_online_spend": avg_online_spend,
        "avg_store_spend": avg_store_spend,
        "discount_sensitivity": discount_sensitivity,
        "return_frequency": return_frequency,
        "avg_delivery_days": avg_delivery_days,
        "delivery_fee_sensitivity": delivery_fee_sensitivity,
        "free_return_importance": free_return_importance,
        "product_availability_online": product_availability_online,
        "impulse_buying_score": impulse_buying_score,
        "need_touch_feel_score": need_touch_feel_score,
        "brand_loyalty_score": brand_loyalty_score,
        "environmental_awareness": environmental_awareness,
        "time_pressure_level": time_pressure_level,
        "gender": gender,
        "city_tier": city_tier,
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        resultado = response.json()

        if resultado["label"] == "Online":
            st.success("Cliente com perfil de compra Online")
        else:
            st.info("Cliente com perfil de compra em Loja física")

        st.metric("Probabilidade de compra online", f"{resultado['probability_online']:.2%}")
        st.json(resultado)

    except requests.exceptions.ConnectionError:
        st.error("Não foi possível conectar na API. Verifique se o FastAPI está rodando.")
    except requests.exceptions.RequestException as erro:
        st.error(f"Erro ao consultar a API: {erro}")
