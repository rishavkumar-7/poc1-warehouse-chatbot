"""
Single source of truth for anything environment-specific.
All other modules read config from here — never read os.environ directly elsewhere.
"""
import os

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
BQ_DATASET = os.getenv("BQ_DATASET", "warehouse_db")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# Business-rule configuration for the estimation engine.
PD_CUTOFF_HOURS = float(os.getenv("PD_CUTOFF_HOURS", "8"))
SPD_FEDEX_CUTOFF_TIME = os.getenv("SPD_FEDEX_CUTOFF_TIME", "17:00")  # HH:MM, 24h
THROUGHPUT_WINDOW_MINUTES = int(os.getenv("THROUGHPUT_WINDOW_MINUTES", "60"))

# Placeholder threshold — flagged in tests/known_limitations.md as needing business sign-off.
AT_RISK_BUFFER_MINUTES = int(os.getenv("AT_RISK_BUFFER_MINUTES", "30"))
