CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE quotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_age INT,
    city VARCHAR(80),
    state VARCHAR(80),
    city_tier INT,
    city_risk_score FLOAT,
    vehicle_type VARCHAR(10),
    vehicle_make VARCHAR(50),
    vehicle_model VARCHAR(80),
    variant VARCHAR(80),
    segment VARCHAR(50),
    fuel_type VARCHAR(20),
    colour VARCHAR(30),
    manufacturing_year INT,
    vehicle_age_years INT,
    engine_cc INT,
    idv FLOAT,
    ncb_percent INT,
    claim_history_count INT,
    policy_type VARCHAR(30),
    usage_type VARCHAR(30),
    previous_insurer VARCHAR(50),
    num_addons INT,
    addons_list TEXT,
    od_premium_before_ncb FLOAT,
    ncb_discount_amount FLOAT,
    tp_premium FLOAT,
    addon_premium FLOAT,
    gst_amount FLOAT,
    predicted_premium FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id VARCHAR(20),
    customer_age INT,
    city VARCHAR(80),
    state VARCHAR(80),
    city_tier INT,
    city_risk_score FLOAT,
    vehicle_type VARCHAR(10),
    vehicle_make VARCHAR(50),
    vehicle_model VARCHAR(80),
    segment VARCHAR(50),
    engine_cc INT,
    manufacturing_year INT,
    vehicle_age_years INT,
    idv FLOAT,
    policy_type VARCHAR(30),
    policy_age_months INT,
    annual_premium_paid FLOAT,
    previous_claims_count INT,
    ncb_at_claim_percent INT,
    zero_dep_addon BOOLEAN,
    engine_protection_addon BOOLEAN,
    usage_type VARCHAR(30),
    rider_experience_years INT,
    helmet_worn BOOLEAN,
    incident_date DATE,
    incident_day_of_week VARCHAR(15),
    incident_month INT,
    incident_time_of_day VARCHAR(15),
    incident_type VARCHAR(50),
    damage_type VARCHAR(80),
    damage_severity_score INT,
    num_parts_affected INT,
    affected_parts TEXT,
    claim_amount FLOAT,
    approval_probability FLOAT,
    claim_approved BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE chat_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT,
    answer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE claim_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_type VARCHAR(10),
    customer_age INT,
    city VARCHAR(80),
    state VARCHAR(80),
    city_tier INT,
    city_risk_score FLOAT,
    vehicle_make VARCHAR(50),
    vehicle_model VARCHAR(80),
    segment VARCHAR(50),
    engine_cc INT,
    vehicle_age_years INT,
    idv FLOAT,
    policy_type VARCHAR(30),
    policy_age_months INT,
    annual_premium_paid FLOAT,
    previous_claims_count INT,
    ncb_at_claim_percent INT,
    zero_dep_addon BOOLEAN,
    engine_protection_addon VARCHAR(20),
    usage_type VARCHAR(30),
    rider_experience_years INT,
    helmet_worn VARCHAR(20),
    incident_day_of_week VARCHAR(15),
    incident_month INT,
    incident_year INT,
    incident_time_of_day VARCHAR(15),
    incident_type VARCHAR(50),
    damage_type VARCHAR(80),
    damage_severity_score INT,
    num_parts_affected INT,
    affected_parts TEXT,
    predicted_claim_amount FLOAT,
    predicted_approval VARCHAR(10),
    predicted_approval_probability FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);




