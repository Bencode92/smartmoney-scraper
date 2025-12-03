"""Configuration SmartMoney Engine v2.3"""
import os
from pathlib import Path

# === CHEMINS ===
ROOT = Path(__file__).parent
DATA_RAW = ROOT / "data" / "raw"
DATA_SP500 = ROOT / "data" / "sp500.json"
OUTPUTS = ROOT / "outputs"
OUTPUTS.mkdir(exist_ok=True)

# === API KEYS ===
TWELVE_DATA_KEY = os.getenv("API_TWELVEDATA", "")
OPENAI_KEY = os.getenv("API_OPENAI", "")

# === SCORING WEIGHTS ===
# Pondération des facteurs dans le score composite
# Total doit faire 1.0
WEIGHTS = {
    "smart_money": 0.45,    # Signal Dataroma (13F, 45j de retard)
    "insider": 0.15,        # Achats/ventes insiders
    "momentum": 0.25,       # RSI + Perf 3M + Position dans range 52w
    "quality": 0.15         # ROE, D/E, Marges, FCF
}

# === SCORING OPTIONS ===
SCORING = {
    "use_zscore": True,         # Normaliser les sous-scores en z-score avant composite
    "sector_neutral_quality": True,  # Quality basé sur ranks sectoriels (vs seuils absolus)
    "smart_money_dedup": True,  # Réduire le double comptage tier/buys
}

# === CONTRAINTES PORTEFEUILLE ===
CONSTRAINTS = {
    "min_positions": 15,
    "max_positions": 25,
    "max_weight": 0.06,        # 6% max par ligne
    "max_sector": 0.30,        # 30% max par secteur
    "min_score": 0.3,          # Score minimum pour inclusion
    "min_price": 5.0,          # Prix minimum $5
    "min_buys": 2              # Minimum 2 achats smart money
}

# === CORRELATION / RISQUE ===
CORRELATION = {
    "use_real_correlation": True,   # Utiliser vraies corrélations (vs approx sectorielle)
    "lookback_days": 252,           # Fenêtre historique pour calcul corrélations
    "shrinkage": 0.2,               # Coefficient shrinkage Ledoit-Wolf (0=aucun, 1=identité)
    "fallback_intra_sector": 0.7,   # Corrélation fallback intra-secteur
    "fallback_inter_sector": 0.4,   # Corrélation fallback inter-secteur
}

# === BACKTEST WALK-FORWARD ===
BACKTEST = {
    "enabled": True,                # Activer le backtest walk-forward
    "rebal_freq": "M",              # Fréquence rebalancement: "W", "M", "Q"
    "tc_bps": 10.0,                 # Coûts de transaction en basis points
    "lookback_days": 252,           # Historique pour calcul métriques
    "risk_free_rate": 0.045,        # Taux sans risque annualisé (4.5%)
    "benchmarks": ["SPY", "CAC"],   # Benchmarks de comparaison
    "cache_prices": True,           # Cacher les prix en local
    "cache_path": "price_cache.parquet",  # Fichier cache
}

# === VALIDATION ===
VALIDATION = {
    "require_outperformance": False,  # Échouer si sous-performance
    "strict_benchmark": True,         # Doit battre SPY ET CAC (vs un seul)
    "min_sharpe": 0.5,                # Sharpe minimum acceptable
    "max_drawdown": -0.25,            # Drawdown max acceptable (-25%)
}

# === TWELVE DATA API ===
TWELVE_DATA_BASE = "https://api.twelvedata.com"

# =============================================================================
# TWELVE DATA API - Configuration par plan
# =============================================================================
# 
# VOTRE PLAN: Ultra (2584 crédits/min)
#
# Crédits par endpoint:
# - Quote, Profile, RSI = 1 crédit chacun
# - TimeSeries (900 jours) = ~5 crédits
# - Statistics = 10 crédits
# - Balance Sheet = 10 crédits
# - Income Statement = 10 crédits
# - Cash Flow = 10 crédits
# - TOTAL par ticker ≈ 48 crédits
#
# Calcul optimal:
# - 2584 crédits/min ÷ 48 crédits/ticker = ~54 tickers/min MAX
# - Avec marge sécurité (10%): ~50 tickers/min
# - 8 appels/ticker → 50 × 8 = 400 req/min théorique
# - On utilise 50 req/min pour être safe (= ~6 tickers/min)
#
# Temps estimé:
# - 70 tickers ≈ 12 minutes
# - 200 tickers ≈ 35 minutes  
# - 500 tickers ≈ 85 minutes (~1h25)
# =============================================================================

# Plan Ultra - Configuration conservative pour éviter les erreurs 429
TWELVE_DATA_RATE_LIMIT = 50  # req/min (conservative pour éviter dépassement crédits)
TWELVE_DATA_TICKER_PAUSE = 1.5  # pause entre tickers (secondes) - laisse respirer l'API

# Mode d'enrichissement
ENRICHMENT_MODE = os.getenv("ENRICHMENT_MODE", "sp500")  # "sp500" ou "smart_money"
ENRICHMENT_TOP_N = int(os.getenv("ENRICHMENT_TOP_N", "500"))  # Nombre de tickers à enrichir

# Cache pour éviter les appels redondants
ENRICHMENT_CACHE = {
    "enabled": True,
    "cache_dir": ROOT / "cache",
    "cache_days": 1,  # Durée de validité du cache (jours)
}

# === OPENAI ===
OPENAI_MODEL = "gpt-4o"
OPENAI_MODEL_FAST = "gpt-4o-mini"
