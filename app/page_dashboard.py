import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


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


@st.cache_data(ttl=60)
def run_query(sql: str) -> pd.DataFrame:
    """Runs a read-only query and returns a DataFrame. Cached for 60s so
    the dashboard stays fast but still refreshes reasonably often."""
    return pd.read_sql(sql, engine)


# ------------------------------------------------------------------
# Access control — simple password gate via session state
# ------------------------------------------------------------------

MANAGER_PASSWORD = os.getenv("MANAGER_PASSWORD", "acko123")  # set MANAGER_PASSWORD in .env for real use

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Manager Login")
    pwd = st.text_input("Enter manager password", type="password")
    if st.button("Login"):
        if pwd == MANAGER_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

st.title("📊 Acko Management Analytics Dashboard")

col_refresh, _ = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ---- KPI Row 1: Claims submitted today / this week / this month ----

claims_time_df = run_query("""
    WITH latest AS (
        SELECT MAX(incident_date) AS max_date FROM claims
    )
    SELECT
        COUNT(*) FILTER (WHERE incident_date = (SELECT max_date FROM latest)) AS today_count,
        COUNT(*) FILTER (WHERE incident_date >= (SELECT max_date - INTERVAL '7 days' FROM latest)) AS week_count,
        COUNT(*) FILTER (WHERE incident_date >= (SELECT max_date - INTERVAL '30 days' FROM latest)) AS month_count
    FROM claims
""")

st.subheader("Claims Volume")
st.caption("Relative to the most recent incident date in the dataset (not real calendar date), since this is historical claims data.")
k1, k2, k3 = st.columns(3)
k1.metric("Claims on Latest Day", int(claims_time_df["today_count"].iloc[0]))
k2.metric("Claims — Last 7 Days", int(claims_time_df["week_count"].iloc[0]))
k3.metric("Claims — Last 30 Days", int(claims_time_df["month_count"].iloc[0]))

# ---- KPI Row 2: Avg predicted claim payout by vehicle type ----

avg_payout_df = run_query("""
    SELECT vehicle_type, AVG(claim_amount) AS avg_claim_amount
    FROM claims
    GROUP BY vehicle_type
""")

st.subheader("Average Claim Payout by Vehicle Type")
payout_cols = st.columns(len(avg_payout_df) if len(avg_payout_df) > 0 else 1)
for i, row in avg_payout_df.iterrows():
    payout_cols[i].metric(
        f"Avg Payout — {row['vehicle_type'].capitalize()}",
        f"₹{row['avg_claim_amount']:,.0f}",
    )

# ---- KPI Row 3: Approval rate, total quotations, avg premium ----

approval_df = run_query("""
    SELECT
        ROUND(100.0 * SUM(CASE WHEN approval_probability >= 0.5 THEN 1 ELSE 0 END) / COUNT(*), 1) AS approval_rate
    FROM claims
""")

quotations_summary_df = run_query("""
    SELECT COUNT(*) AS total_quotations, AVG(predicted_premium) AS avg_premium
    FROM quotations
""")

st.subheader("Approval Rate & Quotations")
k4, k5, k6 = st.columns(3)
k4.metric("Claim Approval Rate", f"{approval_df['approval_rate'].iloc[0]}%")
k5.metric("Total Quotations Generated", int(quotations_summary_df["total_quotations"].iloc[0]))
avg_prem = quotations_summary_df["avg_premium"].iloc[0]
k6.metric("Average Premium Quoted", f"₹{avg_prem:,.0f}" if pd.notnull(avg_prem) else "N/A")

st.divider()

# ---- Chart 1: Top cities by claim volume (Plotly bar chart) ----

st.subheader("Top Cities by Claim Volume")
top_cities_df = run_query("""
    SELECT city, COUNT(*) AS claim_count
    FROM claims
    GROUP BY city
    ORDER BY claim_count DESC
    LIMIT 10
""")
if not top_cities_df.empty:
    fig_cities = px.bar(
        top_cities_df, x="city", y="claim_count",
        labels={"city": "City", "claim_count": "Number of Claims"},
        color="claim_count", color_continuous_scale="Blues",
    )
    st.plotly_chart(fig_cities, use_container_width=True)
else:
    st.info("No claims data available yet.")

# ---- Chart 2: Claim volume trend over time (Altair line chart) ----

st.subheader("Claim Volume Trend Over Time")
trend_df = run_query("""
    SELECT incident_date, COUNT(*) AS claim_count
    FROM claims
    GROUP BY incident_date
    ORDER BY incident_date
""")
if not trend_df.empty:
    trend_df["incident_date"] = pd.to_datetime(trend_df["incident_date"])
    trend_chart = (
        alt.Chart(trend_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("incident_date:T", title="Date"),
            y=alt.Y("claim_count:Q", title="Number of Claims"),
            tooltip=["incident_date:T", "claim_count:Q"],
        )
        .properties(height=350)
        .interactive()
    )
    st.altair_chart(trend_chart, use_container_width=True)
else:
    st.info("No claims data available yet.")

st.divider()

# ---- Chatbot top questions — placeholder until Module 1 is built ----

st.subheader("Top 10 Questions Asked to Chatbot This Week")
try:
    chat_df = run_query("""
        SELECT question, COUNT(*) AS times_asked
        FROM chat_logs
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY question
        ORDER BY times_asked DESC
        LIMIT 10
    """)
    if not chat_df.empty:
        st.dataframe(chat_df, use_container_width=True)
    else:
        st.info("No chatbot activity logged yet.")
except Exception:
    st.info("Chatbot logs not available yet — this section activates once Module 1 (RAG Chatbot) is connected to the chat_logs table.")

st.divider()

# ---- Claims flagged for human review (low approval probability) ----

st.subheader("⚠️ Claims Flagged for Human Review (Approval Probability < 40%)")
flagged_df = run_query("""
    SELECT record_id, vehicle_type, vehicle_model, city, claim_amount, approval_probability, incident_date
    FROM claims
    WHERE approval_probability < 0.40
    ORDER BY approval_probability ASC
    LIMIT 50
""")
if not flagged_df.empty:
    st.dataframe(flagged_df, use_container_width=True)
    st.caption(f"{len(flagged_df)} claims shown (limited to 50). These have low approval probability and may need manual review for possible fraud risk.")
else:
    st.success("No claims currently flagged for review.")
