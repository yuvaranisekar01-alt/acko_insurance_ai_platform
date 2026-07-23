import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

print("DB_NAME being used:", DB_NAME)
print("Full connection string:", DATABASE_URL)


def save_quotation(data: dict, predicted_premium: float):

    with engine.connect() as conn:
        check = conn.execute(text("SELECT current_database(), current_schema();"))
        print("Inside save_quotation:", check.fetchone())

    """
    Inserts a new quotation record into the quotations table.

    data: dict of raw form inputs, keys must match quotations table columns
          (customer_age, city, state, city_tier, city_risk_score, vehicle_type,
           vehicle_make, vehicle_model, variant, segment, fuel_type, colour,
           manufacturing_year, vehicle_age_years, engine_cc, idv, ncb_percent,
           claim_history_count, policy_type, usage_type, previous_insurer,
           num_addons, addons_list)
    predicted_premium: float, the model's predicted annual premium
    """
    insert_query = text("""
        INSERT INTO quotations (
            customer_age, city, state, city_tier, city_risk_score,
            vehicle_type, vehicle_make, vehicle_model, variant, segment,
            fuel_type, colour, manufacturing_year, vehicle_age_years,
            engine_cc, idv, ncb_percent, claim_history_count, policy_type,
            usage_type, previous_insurer, num_addons, addons_list,
            predicted_premium
        ) VALUES (
            :customer_age, :city, :state, :city_tier, :city_risk_score,
            :vehicle_type, :vehicle_make, :vehicle_model, :variant, :segment,
            :fuel_type, :colour, :manufacturing_year, :vehicle_age_years,
            :engine_cc, :idv, :ncb_percent, :claim_history_count, :policy_type,
            :usage_type, :previous_insurer, :num_addons, :addons_list,
            :predicted_premium
        )
    """)

    params = {**data, "predicted_premium": predicted_premium}

    with engine.connect() as conn:
        conn.execute(insert_query, params)
        conn.commit()


def test_connection():
    """Quick sanity check that the DB connection works."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.fetchone() is not None
    
    