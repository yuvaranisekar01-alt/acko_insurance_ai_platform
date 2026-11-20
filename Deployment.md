# Deployment Guide (AWS EC2 + S3)

This is the setup that was actually deployed: one EC2 instance running the Streamlit app and PostgreSQL, with an S3 bucket for model files and claim photos/forms.

## Architecture

```
Browser ──► EC2 (Ubuntu 24.04, t3.small) :8501 ──► Streamlit app (app/main.py)
                  │                                   │
                  │                                   ├─► PostgreSQL (same instance, localhost:5432)
                  │                                   ├─► ChromaDB (local folder data/processed/chroma_db)
                  │                                   ├─► Gemini API (chatbot, embeddings, vision)
                  └── IAM role ──────────────────────► S3 bucket (models/, claims/images/, claims/forms/)
```

Not used in this deployment: RDS (Postgres runs on the EC2 instance) and Docker on the server (a Dockerfile is provided; see below).

## 1. AWS setup
1. Create an AWS account and set a billing/zero-spend budget alert.
2. Launch an EC2 instance: Ubuntu Server 24.04 LTS (x86_64), `t3.small` (2 GiB RAM), 30 GiB storage, with a new key pair (`.pem`).
3. Security group inbound rules (restrict the source to your own IP as `x.x.x.x/32`):
   - SSH, port 22
   - Custom TCP, port 8501 (Streamlit)
   - Do not open port 5432 (PostgreSQL stays local to the instance).
   - Open 8501 to the public only while demonstrating.
4. Create an S3 bucket in the same region (keep "Block all public access" on).
5. Create an IAM role for EC2 with an inline policy allowing `s3:ListBucket` on the bucket and `s3:GetObject` / `s3:PutObject` on `bucket/*`, then attach it to the instance. No access keys are stored anywhere.

## 2. Prepare the server
```bash
ssh -i acko-key.pem ubuntu@<PUBLIC-IP>

sudo apt update && sudo apt upgrade -y

# Swap (the models are large relative to 2 GiB of RAM)
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

sudo apt install -y python3-venv python3-pip python3-dev git postgresql postgresql-contrib tmux build-essential libpq-dev
```

## 3. PostgreSQL
```bash
sudo -u postgres psql
```
```sql
CREATE USER acko WITH PASSWORD '<choose-a-password>';
CREATE DATABASE "acko_Insurance" OWNER acko;
\c "acko_Insurance"
CREATE EXTENSION IF NOT EXISTS pgcrypto;
\q
```
Create the tables from the schema, then load the claims data:
```bash
psql -h localhost -U acko -d acko_Insurance -f db/schema.sql
python src/module04_dashboard/load_claims.py     # run once only; it appends rows
```

## 4. Code and dependencies
```bash
git clone https://github.com/<user>/acko_insurance_ai_platform acko
cd acko
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 5. Large files (not in git)
From your own machine, copy the trained models and the Chroma store, and the raw claims CSVs:
```bash
scp -i acko-key.pem -r models ubuntu@<PUBLIC-IP>:~/acko/
scp -i acko-key.pem -r data/processed/chroma_db ubuntu@<PUBLIC-IP>:~/acko/data/processed/
scp -i acko-key.pem data/raw/acko_*_claims.csv ubuntu@<PUBLIC-IP>:~/acko/data/raw/
```
Upload the model files to S3 as the model store:
```bash
python - <<'EOF'
import boto3, os
s3 = boto3.client("s3", region_name="<region>")
for n in sorted(os.listdir("models")):
    s3.upload_file(f"models/{n}", "<bucket>", f"models/{n}")
EOF
```
The app currently loads models from the local `models/` folder; S3 holds the copy.

## 6. Configuration (`.env`, never committed)
```
DB_USER=acko
DB_PASSWORD=<password>
DB_HOST=localhost
DB_PORT=5432
DB_NAME=acko_Insurance
GEMINI_API_KEY=<key>
MANAGER_PASSWORD=<dashboard-password>
S3_BUCKET=<bucket>
AWS_REGION=<region>
```
```bash
chmod 600 .env
```

## 7. Run
```bash
tmux new -s app
streamlit run app/main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
# detach with Ctrl+B then D
```
Open `http://<PUBLIC-IP>:8501`. The public IP changes whenever the instance is stopped and started.

## 8. Docker (provided, not used on the server)
```bash
docker build -t acko-ai-platform .
docker run --rm --network host --env-file .env \
  -v "$PWD/models:/app/models" \
  -v "$PWD/data:/app/data" \
  acko-ai-platform
```
`--network host` (Linux) lets the container reach the Postgres instance on `localhost`. Models, data and `.env` are mounted at run time, not baked into the image.

## Known issues and notes
- Gemini free-tier limits and occasional 503 "high demand" responses can slow the chatbot and photo analysis.
- Model names change often; if a call returns 404, check the current Gemini model names and update `rag_chatbot.py` / `vision.py`.
- Stop the instance when not in use (Instance state → Stop). Do not leave port 8501 open to the public.

