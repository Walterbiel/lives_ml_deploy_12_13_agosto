import requests
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL")


st.set_page_config(
    page_title="Heart Disease Prediction",
    page_icon="❤️",
    layout="wide"
)

st.title("Heart Disease Prediction")
st.write("Aplicação consumindo uma API FastAPI com modelo de Machine Learning")


col1, col2, col3 = st.columns(3)


with col1:

    age = st.number_input(
        "Idade",
        min_value=18,
        max_value=100,
        value=45
    )

    sex = st.selectbox(
        "Sexo",
        ["Male", "Female"]
    )

    resting_bp_systolic = st.number_input(
        "Pressão Sistólica",
        value=125
    )

    resting_bp_diastolic = st.number_input(
        "Pressão Diastólica",
        value=80
    )

    cholesterol_total = st.number_input(
        "Colesterol Total",
        value=210
    )

    hdl = st.number_input(
        "HDL",
        value=52
    )

    ldl = st.number_input(
        "LDL",
        value=130
    )

    triglycerides = st.number_input(
        "Triglicerídeos",
        value=150
    )


with col2:

    fasting_blood_sugar = st.number_input(
        "Glicemia em jejum",
        value=95
    )

    hba1c = st.number_input(
        "HbA1c",
        value=5.5
    )

    bmi = st.number_input(
        "BMI",
        value=26.3
    )

    resting_heart_rate = st.number_input(
        "Frequência Cardíaca em Repouso",
        value=72
    )

    max_heart_rate_achieved = st.number_input(
        "Frequência Cardíaca Máxima",
        value=165
    )

    chest_pain_type = st.selectbox(
        "Tipo de dor no peito",
        [
            "Typical Angina",
            "Atypical Angina",
            "Non-anginal Pain",
            "Asymptomatic"
        ]
    )

    exercise_induced_angina = st.checkbox(
        "Angina induzida por exercício"
    )

    st_depression = st.number_input(
        "ST Depression",
        value=0.8
    )


with col3:

    family_history = st.checkbox(
        "Histórico familiar"
    )

    smoker_status = st.selectbox(
        "Status de fumante",
        [
            "Never",
            "Former",
            "Current"
        ]
    )

    alcohol_units_per_week = st.number_input(
        "Álcool por semana",
        value=3.0
    )

    exercise_minutes_per_week = st.number_input(
        "Minutos de exercício por semana",
        value=180
    )

    sleep_hours = st.number_input(
        "Horas de sono",
        value=7.5
    )

    stress_score = st.number_input(
        "Nível de stress",
        value=4.2
    )

    wearable_owner = st.checkbox(
        "Possui wearable",
        value=True
    )

    daily_steps = st.number_input(
        "Passos por dia",
        value=9500
    )

    diet_quality_score = st.number_input(
        "Qualidade da dieta",
        value=7.8
    )


if st.button("Realizar previsão"):

    payload = {
        "age": age,
        "sex": sex,
        "resting_bp_systolic": resting_bp_systolic,
        "resting_bp_diastolic": resting_bp_diastolic,
        "cholesterol_total": cholesterol_total,
        "hdl": hdl,
        "ldl": ldl,
        "triglycerides": triglycerides,
        "fasting_blood_sugar": fasting_blood_sugar,
        "hba1c": hba1c,
        "bmi": bmi,
        "resting_heart_rate": resting_heart_rate,
        "max_heart_rate_achieved": max_heart_rate_achieved,
        "chest_pain_type": chest_pain_type,
        "exercise_induced_angina": exercise_induced_angina,
        "st_depression": st_depression,
        "family_history": family_history,
        "smoker_status": smoker_status,
        "alcohol_units_per_week": alcohol_units_per_week,
        "exercise_minutes_per_week": exercise_minutes_per_week,
        "sleep_hours": sleep_hours,
        "stress_score": stress_score,
        "wearable_owner": wearable_owner,
        "daily_steps": daily_steps,
        "diet_quality_score": diet_quality_score
    }

    try:

        response = requests.post(
            API_URL,
            json=payload,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        prediction = result["prediction"]
        probability = result["probability"]

        st.divider()

        st.subheader("Resultado")

        if prediction == 1:

            st.error(
                "Modelo classificou o paciente como risco de doença cardíaca."
            )

        else:

            st.success(
                "Modelo classificou o paciente como sem risco de doença cardíaca."
            )

        st.metric(
            "Probabilidade de doença cardíaca",
            f"{probability:.2%}"
        )

        st.write("Resposta da API:")

        st.json(result)

    except requests.exceptions.ConnectionError:

        st.error(
            "Não foi possível conectar na API. Verifique se o FastAPI está rodando."
        )

    except requests.exceptions.RequestException as error:

        st.error(
            f"Erro ao consultar API: {error}"
        )