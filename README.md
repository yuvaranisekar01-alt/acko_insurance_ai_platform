Acko Insurance AI Platform

An AI-powered insurance platform combining a RAG-based policy chatbot, ML-driven premium and claims prediction, and a live management analytics dashboard — built on synthetic Acko-style data for educational/portfolio purposes.

Project Status
Module	Status	Description
1. RAG Chatbot	✅ Complete	Answers policy questions from Acko FAQ/T&C PDFs
2. Premium Predictor	✅ Complete	ML-based annual premium quoting
3. Claims Assessment	✅ Complete	Photo-based damage analysis + claim amount/approval prediction
4. Management Dashboard	✅ Complete	Live KPIs and charts across all modules
5. Manager AI Assistant	⏳ Not built	Stretch goal — natural language business queries over Postgres

All four completed modules are fully wired to a shared PostgreSQL database, so activity in one module (e.g. chatbot conversations, quotations, claims) is visible in the Module 4 dashboard in real time.

┌─────────────────┐
                    │   PostgreSQL     │
                    │  (shared state)  │
                    │                  │
                    │ quotations       │
                    │ claims           │
                    │ claim_submissions│
                    │ chat_logs        │
                    └────────┬─────────┘
                              │
        ┌──────────┬─────────┼─────────┬──────────┐
        │          │         │         │
   ┌────▼───┐ ┌────▼───┐┌────▼───┐┌────▼─────┐
   │Module 1│ │Module 2││Module 3││ Module 4  │
   │Chatbot │ │Premium ││Claims  ││ Dashboard │
   │        │ │Predictor││Assess.││           │
   │LangChain│ │Sklearn ││Sklearn ││ Plotly/   │
   │+ Chroma│ │+ SHAP  ││+ Gemini││ Altair    │
   │+ Gemini│ │        ││ Vision ││           │
   └────────┘ └────────┘└────────┘└──────────┘

Module 1 — RAG Chatbot

Purpose: Answers customer questions about motor and health insurance policies, grounded strictly in Acko's policy documents (no hallucinated answers).

Tech stack: LangChain (LCEL), ChromaDB, Google Gemini (gemini-embedding-2-preview for embeddings, gemini-3.5-flash for generation)

Key design decision: The system prompt explicitly instructs the model to answer only from retrieved context and to state clearly when information isn't available — verified via out-of-scope test questions (e.g. weather, unrelated insurance products) that correctly return "I don't have that information" rather than a fabricated answer.

Module 2 — Premium Predictor

Purpose: Predicts annual insurance premium for a new car/bike customer, given vehicle, customer, and policy details.

Data: Combined car + bike quotation data (350,000 rows)

Model comparison:

Model	MAE	R²
Linear Regression (baseline)	₹16,940	0.72
Random Forest	₹2,237	0.99
XGBoost	₹2,606	0.99

Random Forest selected as final model (depth constrained to 15 after the initial depth-45 model showed clear overfitting signs; performance held at R²=0.9895 with much faster inference and SHAP compatibility).

Top drivers (SHAP-confirmed): IDV (insured value), Policy Type (Comprehensive vs Third Party), NCB %, vehicle model, city risk score — all directionally consistent with real insurance pricing logic.

Storage: Every quote submitted through the Streamlit form is saved to the quotations table.

Module 3 — Claims Assessment

Purpose: Given an uploaded damage photo and claim details, predicts (a) the likely claim payout amount and (b) approval likelihood.

Design decision — 4 independent models: Rather than one combined model, built separate amount-regression and approval-classification models for cars and bikes, since the two vehicle types have meaningfully different feature sets (e.g. rider_experience_years is bike-only, engine_protection_addon is car-only) and different claim patterns.

Model	Metric	Score
Bike — Claim Amount	R²	0.955
Car — Claim Amount	R²	0.993
Bike — Approval	Accuracy / F1	92.1% / 0.954
Car — Approval	Accuracy / F1	91.3% / 0.948

SHAP insight: The approval models learned recognizable fraud-risk patterns — high claim history, theft/fire damage types, and very new policies at time of claim all push predictions toward rejection.

Known limitation: Photos are analyzed in-session only and are not persisted to cloud storage (AWS S3) — deferred due to project timeline. The pipeline is designed so S3 upload could be added as a drop-in step between photo upload and Vision analysis.

Storage: Every claim submission + prediction is saved to claim_submissions.

Module 4 — Management Dashboard

Purpose: Live business KPIs and visualizations for internal managers, pulling from all other modules' shared data.

Tech stack: Plotly (bar charts), Altair (trend charts), password-gated access

KPIs & charts:

➡️Claims volume (latest day / 7-day / 30-day, relative to the dataset's own most recent date rather than ➡️real calendar time, since claims data is historical)
➡️Average predicted claim payout, by vehicle type
➡️Claim approval rate
➡️Total quotations generated + average premium quoted
➡️Top 10 cities by claim volume (Plotly)
➡️Claim volume trend over time (Altair)
➡️Top 10 chatbot questions this week (from chat_logs)
➡️Claims flagged for human review (approval probability < 40%)

Known Limitations & Future Work
➡️Module 5 (Manager AI Assistant) not built — would use LangChain's SQL agent toolkit over the same Postgres database used by Module 4.
➡️AWS deployment (EC2/RDS/S3) and Docker containerization were scoped in the original brief but deferred given project timeline — the app currently runs locally against a local Postgres instance. Models are stored locally via joblib rather than S3.
➡️Gemini Vision (Module 3) is rate-limited on the free tier (5-15 requests/minute depending on model) — acceptable for demo/portfolio use, would need a paid tier or request queuing for production.
➡️Approval classifier recall on rejected claims (80-87%) still has room for improvement — SMOTE-based oversampling or threshold tuning are natural next steps beyond the class_weight='balanced' fix already applied.

Tech Stack Summary
Category	Tools
ML	scikit-learn, XGBoost, SHAP, category_encoders
LLM / RAG	LangChain, ChromaDB, Google Gemini API
Data	pandas, numpy, PostgreSQL, SQLAlchemy
App	Streamlit
Visualization	Plotly, Altair, matplotlib, seaborn

