import os
import joblib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")

# ------------------------------------------------------------------
# DB connection
# ------------------------------------------------------------------

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# ------------------------------------------------------------------
# Column lists — MUST match the training notebook exactly
# ------------------------------------------------------------------

BIKE_NUM = ['customer_age', 'city_risk_score', 'engine_cc', 'vehicle_age_years',
            'idv', 'policy_age_months', 'annual_premium_paid',
            'previous_claims_count', 'ncb_at_claim_percent', 'zero_dep_addon',
            'rider_experience_years', 'incident_month', 'damage_severity_score',
            'num_parts_affected', 'incident_year']

BIKE_OHE = ["policy_type", "usage_type", "incident_day_of_week",
            "incident_time_of_day", "incident_type", "damage_type",
            "city_tier", "helmet_worn"]

CAR_NUM = ['customer_age', 'city_risk_score', 'engine_cc', 'vehicle_age_years',
           'idv', 'policy_age_months', 'annual_premium_paid',
           'previous_claims_count', 'ncb_at_claim_percent', 'zero_dep_addon',
           'incident_month', 'damage_severity_score', 'num_parts_affected',
           'incident_year']

CAR_OHE = ["policy_type", "incident_day_of_week", "incident_time_of_day",
           "incident_type", "damage_type", "city_tier", "engine_protection_addon"]

TARGET_COLS = ["city", "state", "vehicle_make", "vehicle_model", "segment"]


def load_all_artifacts():
    """Loads all 12 model/encoder artifacts for Module 3. Call once, cache in the app."""
    artifacts = {
        "bike_amount_model": joblib.load(os.path.join(MODELS_DIR, "claims_bike_amount_model.pkl")),
        "car_amount_model": joblib.load(os.path.join(MODELS_DIR, "claims_car_amount_model.pkl")),
        "bike_approved_model": joblib.load(os.path.join(MODELS_DIR, "claims_bike_approved_model.pkl")),
        "car_approved_model": joblib.load(os.path.join(MODELS_DIR, "claims_car_approved_model.pkl")),
        "bike_preprocessor": joblib.load(os.path.join(MODELS_DIR, "claims_bike_preprocessor.pkl")),
        "car_preprocessor": joblib.load(os.path.join(MODELS_DIR, "claims_car_preprocessor.pkl")),
        "bike_mlb": joblib.load(os.path.join(MODELS_DIR, "claims_bike_mlb.pkl")),
        "car_mlb": joblib.load(os.path.join(MODELS_DIR, "claims_car_mlb.pkl")),
        "bike_target_encoder_amount": joblib.load(os.path.join(MODELS_DIR, "claims_bike_target_encoder_amount.pkl")),
        "bike_target_encoder_approved": joblib.load(os.path.join(MODELS_DIR, "claims_bike_target_encoder_approved.pkl")),
        "car_target_encoder_amount": joblib.load(os.path.join(MODELS_DIR, "claims_car_target_encoder_amount.pkl")),
        "car_target_encoder_approved": joblib.load(os.path.join(MODELS_DIR, "claims_car_target_encoder_approved.pkl")),
    }
    return artifacts


def _build_features(raw_input: dict, vehicle_type: str, target: str, artifacts: dict) -> pd.DataFrame:
    """
    Builds the final feature row for either 'amount' or 'approved' target,
    for the given vehicle_type, matching the training-time pipeline exactly.
    """
    input_df = pd.DataFrame([raw_input])

    if vehicle_type == "bike":
        preprocessor = artifacts["bike_preprocessor"]
        mlb = artifacts["bike_mlb"]
        target_encoder = artifacts[f"bike_target_encoder_{target}"]
    else:
        preprocessor = artifacts["car_preprocessor"]
        mlb = artifacts["car_mlb"]
        target_encoder = artifacts[f"car_target_encoder_{target}"]

    # num + ohe
    preprocessed = preprocessor.transform(input_df)
    if hasattr(preprocessed, "toarray"):
        preprocessed = preprocessed.toarray()
    preprocessed_df = pd.DataFrame(preprocessed, columns=preprocessor.get_feature_names_out())

    # multi-label affected_parts
    parts_list = [p.strip() for p in raw_input["affected_parts"].split(",")]
    parts_encoded = mlb.transform([parts_list])
    parts_df = pd.DataFrame(parts_encoded, columns=mlb.classes_)

    # target encoding
    target_encoded_df = target_encoder.transform(input_df[TARGET_COLS]).reset_index(drop=True)

    final_input = pd.concat([preprocessed_df, parts_df, target_encoded_df], axis=1)
    return final_input


def predict_claim(raw_input: dict, vehicle_type: str, artifacts: dict) -> dict:
    """
    Runs both the amount regressor and approval classifier for the given
    vehicle type, returns predicted amount, approval label, and probability.
    """
    amount_features = _build_features(raw_input, vehicle_type, "amount", artifacts)
    approved_features = _build_features(raw_input, vehicle_type, "approved", artifacts)

    amount_model = artifacts[f"{vehicle_type}_amount_model"]
    approved_model = artifacts[f"{vehicle_type}_approved_model"]

    amount_features = amount_features.reindex(columns=amount_model.feature_names_in_, fill_value=0)
    approved_features = approved_features.reindex(columns=approved_model.feature_names_in_, fill_value=0)

    predicted_amount = float(amount_model.predict(amount_features)[0])
    predicted_approved = bool(approved_model.predict(approved_features)[0])
    predicted_approval_probability = float(approved_model.predict_proba(approved_features)[0][1])

    return {
        "predicted_claim_amount": predicted_amount,
        "predicted_approval": "Approved" if predicted_approved else "Rejected",
        "predicted_approval_probability": predicted_approval_probability,
    }


def save_claim_submission(raw_input: dict, prediction: dict):
    """Inserts a new claim submission + prediction result into Postgres."""
    insert_query = text("""
        INSERT INTO claim_submissions (
            vehicle_type, customer_age, city, state, city_tier, city_risk_score,
            vehicle_make, vehicle_model, segment, engine_cc, vehicle_age_years,
            idv, policy_type, policy_age_months, annual_premium_paid,
            previous_claims_count, ncb_at_claim_percent, zero_dep_addon,
            engine_protection_addon, usage_type, rider_experience_years,
            helmet_worn, incident_day_of_week, incident_month, incident_year,
            incident_time_of_day, incident_type, damage_type,
            damage_severity_score, num_parts_affected, affected_parts,
            predicted_claim_amount, predicted_approval, predicted_approval_probability
        ) VALUES (
            :vehicle_type, :customer_age, :city, :state, :city_tier, :city_risk_score,
            :vehicle_make, :vehicle_model, :segment, :engine_cc, :vehicle_age_years,
            :idv, :policy_type, :policy_age_months, :annual_premium_paid,
            :previous_claims_count, :ncb_at_claim_percent, :zero_dep_addon,
            :engine_protection_addon, :usage_type, :rider_experience_years,
            :helmet_worn, :incident_day_of_week, :incident_month, :incident_year,
            :incident_time_of_day, :incident_type, :damage_type,
            :damage_severity_score, :num_parts_affected, :affected_parts,
            :predicted_claim_amount, :predicted_approval, :predicted_approval_probability
        )
    """)
    params = {**raw_input, **prediction}
    with engine.connect() as conn:
        conn.execute(insert_query, params)
        conn.commit()

        