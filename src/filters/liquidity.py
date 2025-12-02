"""SmartMoney v2.3 — Filtres de Liquidité

Exclut les titres illiquides pour éviter:
- Slippage excessif
- Impact de marché
- Positions impossibles à sortir

Date: Décembre 2025
"""

import pandas as pd
import logging
from typing import Optional, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import LIQUIDITY
except ImportError:
    LIQUIDITY = {
        "min_market_cap": 2_000_000_000,
        "min_adv_usd": 5_000_000,
        "max_position_vs_adv": 0.02,
    }

logger = logging.getLogger(__name__)


def apply_liquidity_filters(
    df: pd.DataFrame,
    min_market_cap: Optional[float] = None,
    min_adv_usd: Optional[float] = None,
    max_position_vs_adv: Optional[float] = None,
    position_size_usd: float = 1_000_000,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Filtre l'univers par critères de liquidité.
    
    Args:
        df: DataFrame avec colonnes:
            - market_cap: Capitalisation boursière ($)
            - adv_usd: Average Daily Volume en $ (ou avg_volume + price)
        min_market_cap: Market cap minimum ($). Défaut: config.
        min_adv_usd: ADV minimum ($). Défaut: config.
        max_position_vs_adv: Position max en % de l'ADV. Défaut: config.
        position_size_usd: Taille de position hypothétique pour test.
        verbose: Afficher les logs.
    
    Returns:
        DataFrame filtré (copie).
    
    Example:
        >>> df_filtered = apply_liquidity_filters(universe)
        >>> print(f"Après filtres: {len(df_filtered)} tickers")
    """
    # Valeurs par défaut depuis config
    min_market_cap = min_market_cap or LIQUIDITY["min_market_cap"]
    min_adv_usd = min_adv_usd or LIQUIDITY["min_adv_usd"]
    max_position_vs_adv = max_position_vs_adv or LIQUIDITY["max_position_vs_adv"]
    
    initial_count = len(df)
    df = df.copy()
    
    # === Calculer market_cap si pas présent ===
    if "market_cap" not in df.columns:
        # Essayer de calculer depuis shares_outstanding et price
        if "shares_outstanding" in df.columns:
            price_col = "td_price" if "td_price" in df.columns else "current_price"
            if price_col in df.columns:
                df["market_cap"] = df["shares_outstanding"] * df[price_col]
            else:
                logger.warning("Impossible de calculer market_cap, skip filtre")
                df["market_cap"] = float("inf")
        else:
            logger.warning("Colonne market_cap manquante, skip filtre")
            df["market_cap"] = float("inf")
    
    # === Calculer ADV en $ si pas présent ===
    if "adv_usd" not in df.columns:
        if "td_avg_volume" in df.columns:
            price_col = "td_price" if "td_price" in df.columns else "current_price"
            if price_col in df.columns:
                df["adv_usd"] = df["td_avg_volume"] * df[price_col]
        elif "avg_volume" in df.columns and "price" in df.columns:
            df["adv_usd"] = df["avg_volume"] * df["price"]
        else:
            logger.warning(
                "Colonnes adv_usd ou avg_volume manquantes. "
                "Filtre volume désactivé."
            )
            df["adv_usd"] = float("inf")
    
    # === Appliquer les filtres ===
    
    # 1. Market cap
    mask_mcap = df["market_cap"] >= min_market_cap
    excluded_mcap = (~mask_mcap).sum()
    
    # 2. ADV
    mask_adv = df["adv_usd"] >= min_adv_usd
    excluded_adv = (~mask_adv).sum()
    
    # 3. Position vs ADV
    df["_position_vs_adv"] = position_size_usd / df["adv_usd"].replace(0, 1)
    mask_position = df["_position_vs_adv"] <= max_position_vs_adv
    excluded_position = (~mask_position).sum()
    
    # Combiner
    mask_final = mask_mcap & mask_adv & mask_position
    df_filtered = df[mask_final].copy()
    
    # Nettoyer colonne temporaire
    if "_position_vs_adv" in df_filtered.columns:
        df_filtered = df_filtered.drop(columns=["_position_vs_adv"])
    
    # === Logging ===
    final_count = len(df_filtered)
    excluded_total = initial_count - final_count
    
    if verbose:
        logger.info(
            f"Filtres liquidité: {excluded_total}/{initial_count} exclus "
            f"({final_count} restants)"
        )
        if excluded_total > 0:
            logger.debug(
                f"  - Market cap < ${min_market_cap/1e9:.1f}B: {excluded_mcap}"
            )
            logger.debug(
                f"  - ADV < ${min_adv_usd/1e6:.1f}M: {excluded_adv}"
            )
            logger.debug(
                f"  - Position > {max_position_vs_adv*100:.1f}% ADV: {excluded_position}"
            )
    
    return df_filtered


def check_liquidity_single(
    market_cap: float,
    adv_usd: float,
    position_size_usd: float = 1_000_000,
) -> Dict:
    """
    Vérifie la liquidité d'un seul titre.
    
    Returns:
        Dict avec passes (bool) et détails.
    """
    min_market_cap = LIQUIDITY["min_market_cap"]
    min_adv_usd = LIQUIDITY["min_adv_usd"]
    max_position_vs_adv = LIQUIDITY["max_position_vs_adv"]
    
    position_vs_adv = position_size_usd / adv_usd if adv_usd > 0 else float("inf")
    
    checks = {
        "market_cap_ok": market_cap >= min_market_cap,
        "adv_ok": adv_usd >= min_adv_usd,
        "position_vs_adv_ok": position_vs_adv <= max_position_vs_adv,
    }
    
    return {
        "passes": all(checks.values()),
        "checks": checks,
        "market_cap": market_cap,
        "adv_usd": adv_usd,
        "position_vs_adv_pct": position_vs_adv * 100,
    }
