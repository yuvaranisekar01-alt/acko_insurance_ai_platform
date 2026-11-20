Acko Insurance AI Platform

An end-to-end insurance platform built on synthetic Acko-style data: a RAG chatbot grounded in policy PDFs, ML-based premium quoting, photo-assisted claims assessment, and a live management dashboard. All modules share one PostgreSQL database, and the app is deployed on AWS EC2 with S3 storage.

Data note: all datasets (quotations and claims) are synthetic and were provided for this project. Model scores in this README describe performance on that synthetic data, not on real insurance data.

Project Status
Module	Status	Summary
1. RAG Chatbot	Built	Answers policy questions from 3 Acko PDFs; conversations logged
2. Premium Predictor	Built	Random Forest premium model, SHAP explainability, quotes stored
3. Claims Assessment	Built	Gemini Vision photo analysis + 4 ML models; photos and forms stored in S3
4. Management Dashboard	Built	Live KPIs and charts, password-protected
5. Manager AI Assistant	Not built	Natural-language-to-SQL assistant was out of scope
AWS deployment	Built (see limitations)	EC2 + S3; PostgreSQL runs on the EC2 instance (no RDS)

Architecture

Browser ──► EC2 (Ubuntu 24.04, t3.small) :8501 ──► Streamlit (app/main.py)
                 │                                    │
                 │                                    ├─► PostgreSQL (same instance, localhost)
                 │                                    ├─► ChromaDB (local folder)
                 │                                    ├─► Gemini API (chat, embeddings, vision)
                 └── IAM role ───────────────────────► S3 (models/, claims/images/, claims/forms/)

PostgreSQL tables:

Table	Written by	Contents
quotations	Premium Predictor	Inputs and predicted premium per quote
claims	load_claims.py (one-time)	250,000 historical synthetic claims
claim_submissions	Claims Assessment	New claim inputs and model predictions
chat_logs	Chatbot	Each question and answer


Modules
1. RAG Chatbot

Knowledge base: 3 PDFs (FAQ, Motor policy T&C, Health policy T&C), 595 chunks (RecursiveCharacterTextSplitter, chunk size 800, overlap 100).
Retrieval: Gemini embeddings stored in ChromaDB (persisted in data/processed/chroma_db); top-3 chunks per question.
Generation: LangChain LCEL chain (retriever | format_docs → prompt → LLM → parser). The prompt tells the model to answer only from retrieved context and to say so when the answer is not there. This was checked with out-of-scope questions (weather, unrelated products), which are declined.
Logging: every question and answer is written to chat_logs, which the dashboard reads.
Free-tier note: embedding the 595 chunks required batches of 50 with a pause between batches to stay under rate limits (about 12 minutes).

2. Premium Predictor

Data: 350,000 quotations (150,000 bike + 200,000 car).
Missing values: structural gaps (a bike row has no car-only field) were labelled differently from informative gaps (a car customer with no previous insurer became "First time buyer").
Leakage: the five premium components that sum to the target (od_premium_before_ncb, ncb_discount_amount, tp_premium, addon_premium, gst_amount) were excluded from the features.
Encoding: one-hot for low-cardinality columns, target encoding for high-cardinality ones, MultiLabelBinarizer for the multi-value add-ons list. All encoders were fitted on the training split only.
Feature selection: VIF and Random Forest feature importance.

Model	MAE (₹)	RMSE (₹, from MSE)	R²
Linear Regression (baseline)	16,941	≈ 34,765	0.72
Random Forest (depth ≈ 45)	2,237	≈ 6,474	0.99
XGBoost	2,606	≈ 6,137	0.99
Random Forest, max_depth=15 (final)	2,473	not computed	0.9895

3. Claims Assessment

Photo analysis: an uploaded damage photo is sent to Gemini Vision, which returns damage type, severity (1-10), number of parts and affected parts as JSON. These fill the form for the user to review and edit.
Four independent models: claim amount and approval, separately for bikes and cars (the two vehicle types have different features).
Target meaning: claim_amount is the assessed claim value; rejected claims also carry an amount, so it is not an actual payout.
Leakage: approval_probability (correlation 0.74 with the approval label) was excluded from all models.
Class imbalance: about 87% approved, 13% rejected. class_weight='balanced' raised recall on rejected claims at some cost in precision.
Target encoding was fitted separately against each target.

Model	Result
Bike claim amount	R² 0.955, MAE ₹2,987
Car claim amount	R² 0.993, MAE ₹26,140

Approval model	Accuracy	F1 (approved class)	Macro F1	Rejected recall before → after balancing
Bike	92.1%	0.954	0.83	0.57 → 0.80
Car	91.3%	0.948	0.85	0.65 → 0.87

The balanced setting accepts more false alarms (rejected precision about 0.62-0.65) to miss fewer genuinely rejectable claims, which suits a review workflow. SHAP on the approval models shows claim history, theft and fire damage, and damage severity pushing predictions toward rejection.

4. Management Dashboard

Password-protected (MANAGER_PASSWORD). Shows claim volume for the latest day, last 7 and last 30 days, average claim amount by vehicle type, approval rate, total quotations and average premium, top cities by claim volume (Plotly), claim trend over time (Altair), top chatbot questions this week, and claims flagged for review (approval probability below 40%). The claims data is historical, so the "latest day / 7 / 30 days" cards are measured relative to the newest date in the data, not today's calendar date.

Run Locally
1.Clone the repo and create a virtual environment, then pip install -r requirements.txt.
2.Install PostgreSQL and create a database, then run db/schema.sql against it (it enables the pgcrypto extension).
3.Create .env in the project root
4.Put the raw CSVs in data/raw/ (acko_bike_claims.csv, acko_car_claims.csv), then load the claims once from the project root.

AWS Deployment (EC2 + S3)

This is the setup that was deployed. The same steps with more detail are in DEPLOYMENT.md.

1. Account and safety

Create an AWS account, complete identity verification, and set a zero-spend budget alert.
Secure the login with a second factor. Stop the instance when it is not in use.

2. EC2 instance

Ubuntu Server 24.04 LTS (x86_64), t3.small (2 GiB RAM), 30 GiB storage, new key pair (.pem, never committed).
Security group inbound rules, with the source set to your own IP (x.x.x.x/32): SSH (22) and Custom TCP 8501. Do not open 5432. Open 8501 publicly only during a demo.
The public IP changes every time the instance is stopped and started.

Docker (provided): Dockerfile and .dockerignore build an image containing only the code; models, data and .env are mounted at run time. This was written from the deployment steps above and the app was deployed directly on EC2, so the image build has not been verified on the server.

Key Design Decisions

Leakage checks before modelling: removed target components (premium), and a column derived from the label (approval_probability); fitted every encoder on training data only.
Overfitting: capped Random Forest depth at 15 after the first model showed very deep trees.
Imbalance: chose recall on rejected claims over headline accuracy and documented the trade-off.
Separate models per vehicle type: features differ between bikes and cars.
Grounded chatbot: retrieval plus a prompt that refuses to answer outside the documents.
No stored AWS keys: the instance uses an IAM role.

Known Limitations

Module 5 (text-to-SQL manager assistant) was not built.
The chatbot only answers policy questions. It does not route requests to the quotation or claims forms, which the original brief described.
No user accounts: quotations and claims are stored with timestamps but no user ID.
PostgreSQL runs on the EC2 instance, not on RDS.
Models are loaded from local disk. S3 holds a copy and the claims photos and forms, but the app does not download models from S3 at startup.
Evaluation is a single train/test split on synthetic data; there is no cross-validation or hyperparameter search. The very high premium R² reflects how closely the synthetic premium follows a few inputs and should not be expected on real data.
The app is served over plain HTTP on port 8501, restricted to an allowed IP, with no domain or HTTPS.
Gemini free-tier limits and demand spikes (rate limits, occasional 503 errors) can slow the chatbot and photo analysis. Gemini model names change often; update the names in rag_chatbot.py and vision.py if a call returns 404.
Docker image not verified on the server.

Tech Stack

Python 3.12, scikit-learn, XGBoost, SHAP, category_encoders, pandas, NumPy · LangChain, ChromaDB, Google Gemini · PostgreSQL, SQLAlchemy · Streamlit, Plotly, Altair · AWS EC2, S3, IAM · Docker

