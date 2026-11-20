FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build tools are only needed if a dependency has no prebuilt wheel
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code only. models/, data/ and .env are NOT copied into the image:
# models and the Chroma store are large, and secrets must never be baked in.
COPY app ./app
COPY src ./src
COPY db ./db

EXPOSE 8501

CMD ["streamlit", "run", "app/main.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
