import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# ---- Adjust these paths if your raw CSVs live elsewhere ----
BIKE_CLAIMS_PATH = r"C:\projects\acko_insurance_ai_platform\data\raw\acko_bike_claims.csv"
CAR_CLAIMS_PATH = r"C:\projects\acko_insurance_ai_platform\data\raw\acko_car_claims.csv"

bike_claims = pd.read_csv(BIKE_CLAIMS_PATH)
car_claims = pd.read_csv(CAR_CLAIMS_PATH)

bike_claims["vehicle_type"] = "bike"
car_claims["vehicle_type"] = "car"

combined = pd.concat([bike_claims, car_claims], ignore_index=True)

# bike-only / car-only columns -> fill NaN sensibly for storage
if "usage_type" in combined.columns:
    combined["usage_type"] = combined["usage_type"].fillna("Not Applicable - Car")
if "rider_experience_years" in combined.columns:
    combined["rider_experience_years"] = combined["rider_experience_years"].fillna(-1)
if "helmet_worn" in combined.columns:
    combined["helmet_worn"] = combined["helmet_worn"].astype("boolean")
if "engine_protection_addon" in combined.columns:
    combined["engine_protection_addon"] = combined["engine_protection_addon"].astype("boolean")
if "zero_dep_addon" in combined.columns:
    combined["zero_dep_addon"] = combined["zero_dep_addon"].astype("boolean")
if "claim_approved" in combined.columns:
    combined["claim_approved"] = combined["claim_approved"].astype("boolean")

# only keep columns that actually exist in the claims table
claims_table_cols = [
    "record_id", "customer_age", "city", "state", "city_tier", "city_risk_score",
    "vehicle_type", "vehicle_make", "vehicle_model", "segment", "engine_cc",
    "manufacturing_year", "vehicle_age_years", "idv", "policy_type",
    "policy_age_months", "annual_premium_paid", "previous_claims_count",
    "ncb_at_claim_percent", "zero_dep_addon", "engine_protection_addon",
    "usage_type", "rider_experience_years", "helmet_worn", "incident_date",
    "incident_day_of_week", "incident_month", "incident_time_of_day",
    "incident_type", "damage_type", "damage_severity_score",
    "num_parts_affected", "affected_parts", "claim_amount",
    "approval_probability", "claim_approved",
]
combined = combined[[c for c in claims_table_cols if c in combined.columns]]

combined["incident_date"] = pd.to_datetime(combined["incident_date"]).dt.date
combined.to_sql("claims", engine, if_exists="append", index=False)

print(f"Loaded {len(combined)} rows into claims table.")

