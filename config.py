"""Configuration SmartMoney Engine v2.1"""
import os
from pathlib import Path

# === CHEMINS ===
ROOT = Path(__file__).parent
DATA_RAW = ROOT / "data" / "raw"
OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)

# === API KEYS ===
TWELVE_DATA_KEY = os.getenv("API_TWELVEDATA", "")
OPENAI_KEY = os.getenv("API_OPENAI", "")

# === SCORING WEIGHTS ===
WEIGHTS = {
    "smart_money": 0.45,
    "insider": 0.15,
    "momentum": 0.25,
    "quality": 0.15
}

# === CONTRAINTES PORTEFEUILLE ===
CONSTRAINTS = {
    "min_positions": 15,
    "max_positions": 25,
    "max_weight": 0.06,            # 6% max par ligne
    "max_sector": 0.30,            # 30% max par secteur
    "min_score": 0.3,              # Score minimum pour inclusion
    "min_price": 5.0,              # Prix minimum $5
    "min_buys": 2,                 # Minimum 2 achats smart money
    "min_avg_volume": 100_000,     # Volume moyen minimum (liquidité)
    "min_fundamentals_coverage": 0.5  # 50% minimum avec fondamentaux
}

# === TWELVE DATA ===
TWELVE_DATA_BASE = "https://api.twelvedata.com"
TWELVE_DATA_RATE_LIMIT = 80  # Réduit de 120 à 80 pour marge de sécurité

# === OPENAI ===
OPENAI_MODEL = "gpt-4o"
OPENAI_MODEL_FAST = "gpt-4o-mini"
