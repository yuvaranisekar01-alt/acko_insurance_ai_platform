import streamlit as st

st.set_page_config(page_title="Acko Insurance AI Platform", layout="wide")

chatbot_page = st.Page("page_chatbot.py", title="Policy Chatbot", icon="💬")
premium_page = st.Page("page_premium.py", title="Premium Predictor", icon="💰")
claims_page = st.Page("page_claims.py", title="Claims Assessment", icon="🔧")
dashboard_page = st.Page("page_dashboard.py", title="Manager Dashboard", icon="📊")

pg = st.navigation(
    {
        "Customer Tools": [chatbot_page, premium_page, claims_page],
        "Internal": [dashboard_page],
    }
)

pg.run()

