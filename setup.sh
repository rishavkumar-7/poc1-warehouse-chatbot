#!/usr/bin/env bash
# setup.sh — one-shot environment setup for POC1 (AI-Powered Warehouse Operations Assistant).
# Run this from inside the cloned repo: `bash setup.sh` (or `./setup.sh` after chmod +x).
# Safe to re-run — steps that are already done (dataset exists, ADC already set up) are skipped.

set -euo pipefail

# ---- 0. Sanity check: are we actually inside the repo? ----
if [ ! -f "requirements.txt" ] || [ ! -d "db" ]; then
    echo "Error: run this from inside the poc1-warehouse-chatbot repo root (requirements.txt / db/ not found here)."
    exit 1
fi

echo "== 1. Installing Python dependencies =="
pip install -r requirements.txt

echo "== 2. Resolving project config =="
export GCP_PROJECT_ID="$(gcloud config get-value project)"
export BQ_DATASET="warehouse_db"
export GCP_LOCATION="${GCP_LOCATION:-us-central1}"
echo "Project: $GCP_PROJECT_ID | Dataset: $BQ_DATASET | Location: $GCP_LOCATION"

echo "== 3. Enabling required APIs =="
gcloud services enable bigquery.googleapis.com aiplatform.googleapis.com

echo "== 4. Creating BigQuery dataset (skips if it already exists) =="
if bq show "${GCP_PROJECT_ID}:${BQ_DATASET}" >/dev/null 2>&1; then
    echo "Dataset ${BQ_DATASET} already exists — skipping."
else
    bq mk --dataset "${GCP_PROJECT_ID}:${BQ_DATASET}"
fi

echo "== 5. Loading schema =="
export project="$GCP_PROJECT_ID"
export dataset="$BQ_DATASET"
envsubst < db/schema.sql | bq query --use_legacy_sql=false

echo "== 6. Loading seed data =="
envsubst < db/seed_data.sql | bq query --use_legacy_sql=false

echo "== 7. Verifying data landed =="
bq query --use_legacy_sql=false "SELECT * FROM \`${GCP_PROJECT_ID}.${BQ_DATASET}.shipments\`"

echo "== 8. Writing .env so config persists across new terminal tabs =="
cat > .env << EOF
GCP_PROJECT_ID=${GCP_PROJECT_ID}
BQ_DATASET=${BQ_DATASET}
GCP_LOCATION=${GCP_LOCATION}
EOF
echo ".env written."

echo "== 9. Application Default Credentials =="
ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"
if [ -f "$ADC_FILE" ]; then
    echo "ADC already set up — skipping login. Delete $ADC_FILE first if you need to redo it."
else
    echo "Opening the auth flow — follow the link, sign in, and paste the code back here."
    gcloud auth application-default login
fi

echo "== 10. Verifying the ADK import =="
python3 -c "from google.adk import Agent; print('google.adk import OK')"

echo ""
echo "Setup complete. Next steps:"
echo "  Terminal tab 1: uvicorn api.main:app --host 0.0.0.0 --port 8000"
echo "  Terminal tab 2: streamlit run ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0"
echo "  Then open Web Preview on port 8501."