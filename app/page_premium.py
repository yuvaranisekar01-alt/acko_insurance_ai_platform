import streamlit as st
import pandas as pd
import numpy as np
import joblib
import datetime
import sys
import os

# allow importing db.py from src/module2_premium/
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "module02_premium"))
from db import save_quotation  # noqa: E402

# ------------------------------------------------------------------
# Load model + encoders (cached so they only load once per session)
# ------------------------------------------------------------------

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


@st.cache_resource
def load_artifacts():
    model = joblib.load(os.path.join(MODELS_DIR, "rf_model.pkl"))
    preprocessor = joblib.load(os.path.join(MODELS_DIR, "preprocessor.pkl"))
    target_encoder = joblib.load(os.path.join(MODELS_DIR, "target_encoder.pkl"))
    mlb = joblib.load(os.path.join(MODELS_DIR, "mlb_addons.pkl"))
    return model, preprocessor, target_encoder, mlb


model, preprocessor, target_encoder, mlb = load_artifacts()

# ------------------------------------------------------------------
# Column lists — MUST match training notebook exactly
# ------------------------------------------------------------------

NUM_COLS = [
    "customer_age", "city_risk_score", "engine_cc", "manufacturing_year",
    "idv", "ncb_percent", "claim_history_count", "num_addons",
]
OHE_COLS = [
    "fuel_type", "policy_type", "usage_type", "vehicle_type",
    "previous_insurer", "city_tier",
]
TARGET_COLS = [
    "vehicle_make", "vehicle_model", "variant", "segment",
    "colour", "city", "state",
]

ADDON_OPTIONS = [
    "Zero Depreciation", "Engine Protection", "Roadside Assistance",
    "Consumables Cover", "Return to Invoice", "Pillion Rider Cover",
    "Passenger Cover", "Tyre Protection", "Key Replacement",
    "No Claim Bonus Protection", "Personal Accident Cover",
]

CURRENT_YEAR = datetime.datetime.now().year

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------

st.title("🚗 Acko Premium Predictor")
st.caption("Get an instant estimated annual premium for a car or bike policy.")

with st.form("premium_form"):
    st.subheader("Customer Details")
    col1, col2 = st.columns(2)
    with col1:
        customer_age = st.number_input("Customer Age", min_value=18, max_value=100, value=30)
        city = st.text_input("City", value="Bengaluru")
    with col2:
        state = st.text_input("State", value="Karnataka")
        city_tier = st.selectbox("City Tier", [1, 2, 3], index=0)

    city_risk_score = st.slider("City Risk Score", 0.0, 2.0, 1.0, step=0.01)

    st.subheader("Vehicle Details")
    col3, col4 = st.columns(2)
    with col3:
        vehicle_type = st.selectbox("Vehicle Type", ["car", "bike"])
        vehicle_make = st.text_input("Vehicle Make", value="Maruti")
        vehicle_model = st.text_input("Vehicle Model", value="Swift")
        variant = st.text_input("Variant", value="VXI")
    with col4:
        segment = st.text_input("Segment", value="hatchback")
        fuel_type = st.selectbox("Fuel Type", ["Petrol", "Diesel", "Electric", "CNG", "Hybrid", "LPG"])
        colour = st.text_input("Colour", value="White")
        engine_cc = st.number_input("Engine CC", min_value=50, max_value=6000, value=1200)

    manufacturing_year = st.number_input(
        "Manufacturing Year", min_value=CURRENT_YEAR - 25, max_value=CURRENT_YEAR, value=CURRENT_YEAR - 3
    )

    st.subheader("Policy Details")
    col5, col6 = st.columns(2)
    with col5:
        idv = st.number_input("IDV (₹)", min_value=10000, max_value=10000000, value=500000, step=1000)
        ncb_percent = st.selectbox("NCB %", [0, 20, 25, 35, 45, 50], index=0)
        claim_history_count = st.number_input("Previous Claims Count", min_value=0, max_value=20, value=0)
    with col6:
        policy_type = st.selectbox("Policy Type", ["Comprehensive", "Third Party", "Own Damage"])
        usage_type = st.selectbox("Usage Type (bikes only)", ["Personal", "Delivery", "Not Applicable - Bike"])
        previous_insurer = st.text_input("Previous Insurer (leave blank if none)", value="")

    addons_selected = st.multiselect("Add-ons", ADDON_OPTIONS)

    submitted = st.form_submit_button("Get Premium Estimate")

# ------------------------------------------------------------------
# Prediction logic
# ------------------------------------------------------------------

if submitted:
    vehicle_age_years = CURRENT_YEAR - manufacturing_year
    num_addons = len(addons_selected)
    addons_list_str = ", ".join(addons_selected) if addons_selected else "No addons"
    previous_insurer_final = previous_insurer.strip() if previous_insurer.strip() else "First time buyer"

    raw_input = {
        "customer_age": customer_age,
        "city_risk_score": city_risk_score,
        "engine_cc": engine_cc,
        "manufacturing_year": manufacturing_year,
        "idv": idv,
        "ncb_percent": ncb_percent,
        "claim_history_count": claim_history_count,
        "num_addons": num_addons,
        "fuel_type": fuel_type,
        "policy_type": policy_type,
        "usage_type": usage_type,
        "vehicle_type": vehicle_type,
        "previous_insurer": previous_insurer_final,
        "city_tier": city_tier,
        "vehicle_make": vehicle_make,
        "vehicle_model": vehicle_model,
        "variant": variant,
        "segment": segment,
        "colour": colour,
        "city": city,
        "state": state,
    }

    input_df = pd.DataFrame([raw_input])

    # 1. numerical + one-hot via saved ColumnTransformer
    preprocessed = preprocessor.transform(input_df)
    if hasattr(preprocessed, "toarray"):
        preprocessed = preprocessed.toarray()
    preprocessed_df = pd.DataFrame(
        preprocessed, columns=preprocessor.get_feature_names_out()
    )

    # 2. target encoding for high-cardinality columns
    target_encoded_df = target_encoder.transform(input_df[TARGET_COLS])
    target_encoded_df = target_encoded_df.reset_index(drop=True)

    # 3. multi-label binarize the addons
    addons_list_for_mlb = [a.strip() for a in addons_list_str.split(",")]
    addons_encoded = mlb.transform([addons_list_for_mlb])
    addons_encoded_df = pd.DataFrame(addons_encoded, columns=mlb.classes_)

    # 4. combine in the SAME order used during training
    final_input = pd.concat(
        [preprocessed_df, addons_encoded_df, target_encoded_df], axis=1
    )

    # 5. align columns to exactly what the model was trained on
    final_input = final_input.reindex(columns=model.feature_names_in_, fill_value=0)

    # 6. predict
    predicted_premium = float(model.predict(final_input)[0])

    st.success(f"### Estimated Annual Premium: ₹{predicted_premium:,.2f}")

    # 7. save to Postgres
    try:
        save_quotation(
            data={
                "customer_age": customer_age,
                "city": city,
                "state": state,
                "city_tier": city_tier,
                "city_risk_score": city_risk_score,
                "vehicle_type": vehicle_type,
                "vehicle_make": vehicle_make,
                "vehicle_model": vehicle_model,
                "variant": variant,
                "segment": segment,
                "fuel_type": fuel_type,
                "colour": colour,
                "manufacturing_year": manufacturing_year,
                "vehicle_age_years": vehicle_age_years,
                "engine_cc": engine_cc,
                "idv": idv,
                "ncb_percent": ncb_percent,
                "claim_history_count": claim_history_count,
                "policy_type": policy_type,
                "usage_type": usage_type,
                "previous_insurer": previous_insurer_final,
                "num_addons": num_addons,
                "addons_list": addons_list_str,
            },
            predicted_premium=predicted_premium,
        )
        st.info("Quotation saved to database.")
    except Exception as e:
        st.warning(f"Prediction succeeded, but saving to database failed: {e}")

