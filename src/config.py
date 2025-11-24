"""
Configuration globale pour le scraper SmartMoney.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# --- Clés API ---
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

# --- Configuration HTTP ---
HTTP_USER_AGENT = os.getenv(
    "HTTP_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
)
REQUESTS_SLEEP_SECONDS = float(os.getenv("REQUESTS_SLEEP_SECONDS", "2"))
MAX_RETRIES = 3
TIMEOUT_SECONDS = 15

# --- Paramètres de scraping ---
HEDGEFOLLOW_TOP_N_FUNDS = int(os.getenv("HEDGEFOLLOW_TOP_N_FUNDS", "15"))
DATAROMA_TOP_N_MANAGERS = int(os.getenv("DATAROMA_TOP_N_MANAGERS", "10"))
INSIDER_MIN_VALUE_USD = int(os.getenv("INSIDER_MIN_VALUE_USD", "5000000"))
INSIDER_DAYS_BACK = int(os.getenv("INSIDER_DAYS_BACK", "7"))

# --- URLs de base ---
HEDGEFOLLOW_BASE_URL = "https://hedgefollow.com"
DATAROMA_BASE_URL = "https://www.dataroma.com/m"

# --- Chemins des données ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

RAW_HF_DIR = RAW_DATA_DIR / "hedgefollow"
RAW_DTR_DIR = RAW_DATA_DIR / "dataroma"

for dir_path in [RAW_HF_DIR, RAW_DTR_DIR, PROCESSED_DATA_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "smartmoney.db"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# --- Date format ---
DATE_FORMAT = "%Y%m%d"  # Pour les noms de fichiers
