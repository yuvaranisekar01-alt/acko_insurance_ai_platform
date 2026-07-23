import streamlit as st
import sys
import os
import datetime
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "module03_claims"))
from vision import extract_damage_info  # noqa: E402
from predictor import load_all_artifacts, predict_claim, save_claim_submission  # noqa: E402


CURRENT_YEAR = datetime.datetime.now().year


@st.cache_resource
def get_artifacts():
    return load_all_artifacts()


artifacts = get_artifacts()

st.title("🔧 Acko Claims Damage Assessment")
st.caption("Upload a damage photo to auto-extract damage details, then fill in the remaining claim info.")

# ------------------------------------------------------------------
# Step 1: Photo upload + Gemini Vision extraction
# ------------------------------------------------------------------

st.subheader("1. Upload Damage Photo")
uploaded_file = st.file_uploader("Upload a photo of the vehicle damage", type=["jpg", "jpeg", "png"])

if "vision_result" not in st.session_state:
    st.session_state.vision_result = None

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded damage photo", use_container_width=True)

    if st.button("Analyze Damage with AI"):
        with st.spinner("Analyzing photo..."):
            try:
                st.session_state.vision_result = extract_damage_info(image)
                st.success("Damage analysis complete — review and adjust below if needed.")
            except Exception as e:
                st.error(f"Could not analyze image: {e}")
                st.session_state.vision_result = None

vision = st.session_state.vision_result or {
    "damage_type": "dent",
    "damage_severity_score": 3,
    "num_parts_affected": 1,
    "affected_parts": "front bumper",
}

# ------------------------------------------------------------------
# Step 2: Claim form (pre-filled from vision result where available)
# ------------------------------------------------------------------

st.subheader("2. Claim Details")

with st.form("claim_form"):
    vehicle_type = st.selectbox("Vehicle Type", ["car", "bike"])

    col1, col2 = st.columns(2)
    with col1:
        customer_age = st.number_input("Customer Age", min_value=18, max_value=100, value=30)
        city = st.text_input("City", value="Bengaluru")
        state = st.text_input("State", value="Karnataka")
        city_tier = st.selectbox("City Tier", [1, 2, 3])
        city_risk_score = st.slider("City Risk Score", 0.0, 2.0, 1.0, step=0.01)
        vehicle_make = st.text_input("Vehicle Make", value="Maruti")
        vehicle_model = st.text_input("Vehicle Model", value="Swift")
        segment = st.text_input("Segment", value="hatchback")
        engine_cc = st.number_input("Engine CC", min_value=50, max_value=6000, value=1200)
        vehicle_age_years = st.number_input("Vehicle Age (years)", min_value=0, max_value=30, value=3)

    with col2:
        idv = st.number_input("IDV (₹)", min_value=10000, max_value=10000000, value=500000, step=1000)
        policy_type = st.selectbox("Policy Type", ["Comprehensive", "Third Party", "Own Damage"])
        policy_age_months = st.number_input("Policy Age (months)", min_value=0, max_value=240, value=12)
        annual_premium_paid = st.number_input("Annual Premium Paid (₹)", min_value=0, value=8000)
        previous_claims_count = st.number_input("Previous Claims Count", min_value=0, max_value=20, value=0)
        ncb_at_claim_percent = st.selectbox("NCB % at Claim", [0, 20, 25, 35, 45, 50])
        zero_dep_addon = st.checkbox("Zero Depreciation Add-on")
        engine_protection_addon = st.selectbox("Engine Protection Add-on (cars only)", ["True", "False", "Not available"])
        usage_type = st.selectbox("Usage Type (bikes only)", ["Personal", "Delivery", "Not Applicable - Car"])
        rider_experience_years = st.number_input("Rider Experience (years, bikes only)", min_value=-1, max_value=50, value=-1)
        helmet_worn = st.selectbox("Helmet Worn (bikes only)", ["True", "False", "None"])

    st.markdown("**Incident Details**")
    col3, col4 = st.columns(2)
    with col3:
        incident_day_of_week = st.selectbox("Incident Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        incident_month = st.selectbox("Incident Month", list(range(1, 13)))
        incident_year = st.number_input("Incident Year", min_value=2015, max_value=CURRENT_YEAR, value=CURRENT_YEAR)
    with col4:
        incident_time_of_day = st.selectbox("Incident Time of Day", ["Morning", "Afternoon", "Evening", "Night"])
        incident_type = st.selectbox("Incident Type", ["Collision", "Fire", "Theft", "Vandalism", "Natural Disaster", "Other"])

    st.markdown("**Damage Details** (auto-filled from photo analysis — adjust if needed)")
    col5, col6 = st.columns(2)
    with col5:
        damage_type = st.text_input("Damage Type", value=vision["damage_type"])
        damage_severity_score = st.slider("Damage Severity Score", 1, 10, int(vision["damage_severity_score"]))
    with col6:
        num_parts_affected = st.number_input("Number of Parts Affected", min_value=1, max_value=20, value=int(vision["num_parts_affected"]))
        affected_parts = st.text_input("Affected Parts (comma-separated)", value=vision["affected_parts"])

    submitted = st.form_submit_button("Predict Claim Outcome")

# ------------------------------------------------------------------
# Step 3: Prediction
# ------------------------------------------------------------------

if submitted:
    raw_input = {
        "customer_age": customer_age,
        "city": city,
        "state": state,
        "city_tier": city_tier,
        "city_risk_score": city_risk_score,
        "vehicle_make": vehicle_make,
        "vehicle_model": vehicle_model,
        "segment": segment,
        "engine_cc": engine_cc,
        "vehicle_age_years": vehicle_age_years,
        "idv": idv,
        "policy_type": policy_type,
        "policy_age_months": policy_age_months,
        "annual_premium_paid": annual_premium_paid,
        "previous_claims_count": previous_claims_count,
        "ncb_at_claim_percent": ncb_at_claim_percent,
        "zero_dep_addon": zero_dep_addon,
        "engine_protection_addon": engine_protection_addon,
        "usage_type": usage_type,
        "rider_experience_years": rider_experience_years,
        "helmet_worn": helmet_worn,
        "incident_day_of_week": incident_day_of_week,
        "incident_month": incident_month,
        "incident_year": incident_year,
        "incident_time_of_day": incident_time_of_day,
        "incident_type": incident_type,
        "damage_type": damage_type,
        "damage_severity_score": damage_severity_score,
        "num_parts_affected": num_parts_affected,
        "affected_parts": affected_parts,
    }

    prediction = predict_claim(raw_input, vehicle_type, artifacts)

    st.subheader("3. Prediction Result")
    col_a, col_b = st.columns(2)
    col_a.metric("Predicted Claim Amount", f"₹{prediction['predicted_claim_amount']:,.0f}")
    col_b.metric(
        "Predicted Outcome",
        prediction["predicted_approval"],
        f"{prediction['predicted_approval_probability']*100:.1f}% approval probability",
    )

    try:
        save_claim_submission({**raw_input, "vehicle_type": vehicle_type}, prediction)
        st.info("Claim submission saved to database.")
    except Exception as e:
        st.warning(f"Prediction succeeded, but saving to database failed: {e}")

