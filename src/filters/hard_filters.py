"""SmartMoney v2.3 — Hard Filters (Exclusion)

Filtres binaires d'exclusion basés sur le risque financier.
Appliqués AVANT le scoring.

Logique:
- should_exclude = True → titre JAMAIS sélectionnable
- Pas de nuances, pas de scores partiels

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, Optional, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import HARD_FILTERS
except ImportError:
    HARD_FILTERS = {
        "max_debt_equity": 3.0,
        "max_debt_ebitda": 4.0,
        "min_interest_coverage": 2.5,
    }

logger = logging.getLogger(__name__)


def apply_hard_filters(
    df: pd.DataFrame,
    max_debt_equity: Optional[float] = None,
    max_debt_ebitda: Optional[float] = None,
    min_interest_coverage: Optional[float] = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Applique les filtres hard d'exclusion.
    
    Args:
        df: DataFrame avec colonnes:
            - total_debt ou debt_equity: Dette ou ratio
            - equity: Capitaux propres
            - ebitda (ou ebit): EBITDA ou EBIT
            - interest_expense: Charges d'intérêts
            - cash (optionnel): Trésorerie
        max_debt_equity: D/E maximum. Défaut: config.
        max_debt_ebitda: ND/EBITDA maximum. Défaut: config.
        min_interest_coverage: Coverage minimum. Défaut: config.
        verbose: Afficher les logs.
    
    Returns:
        DataFrame filtré (copie) avec colonne 'exclude_reason' pour debug.
    """
    # Valeurs par défaut
    max_debt_equity = max_debt_equity or HARD_FILTERS["max_debt_equity"]
    max_debt_ebitda = max_debt_ebitda or HARD_FILTERS["max_debt_ebitda"]
    min_interest_coverage = min_interest_coverage or HARD_FILTERS["min_interest_coverage"]
    
    initial_count = len(df)
    df = df.copy()
    
    # Initialiser les colonnes de tracking
    df["_exclude"] = False
    df["_exclude_reason"] = ""
    
    excluded_de = 0
    excluded_nd = 0
    excluded_cov = 0
    
    # === 1. Debt/Equity ===
    # Utiliser debt_equity si déjà calculé, sinon calculer
    if "debt_equity" in df.columns:
        de_series = df["debt_equity"]
    elif "total_debt" in df.columns and "equity" in df.columns:
        de_series = df["total_debt"] / df["equity"].replace(0, np.nan)
    else:
        logger.warning("Colonnes D/E manquantes, skip filtre")
        de_series = pd.Series([np.nan] * len(df))
    
    mask_de = de_series > max_debt_equity
    mask_de = mask_de.fillna(False)
    df.loc[mask_de, "_exclude"] = True
    df.loc[mask_de, "_exclude_reason"] += "D/E; "
    excluded_de = mask_de.sum()
    
    # === 2. Net Debt / EBITDA ===
    if "total_debt" in df.columns:
        # EBITDA = EBIT × 1.2 si pas disponible (approximation)
        if "ebitda" in df.columns:
            ebitda = df["ebitda"]
        elif "ebit" in df.columns:
            ebitda = df["ebit"] * 1.2
        else:
            ebitda = pd.Series([np.nan] * len(df))
        
        cash = df.get("cash", pd.Series([0] * len(df)))
        net_debt = df["total_debt"] - cash
        nd_ebitda = net_debt / ebitda.replace(0, np.nan)
        
        mask_nd = nd_ebitda > max_debt_ebitda
        mask_nd = mask_nd.fillna(False)
        df.loc[mask_nd, "_exclude"] = True
        df.loc[mask_nd, "_exclude_reason"] += "ND/EBITDA; "
        excluded_nd = mask_nd.sum()
    
    # === 3. Interest Coverage ===
    if "ebit" in df.columns:
        # Chercher interest_expense ou l'estimer
        if "interest_expense" in df.columns:
            int_exp = df["interest_expense"].abs().replace(0, np.nan)
        elif "total_debt" in df.columns:
            # Estimer à 5% de la dette
            int_exp = df["total_debt"] * 0.05
            int_exp = int_exp.replace(0, np.nan)
        else:
            int_exp = pd.Series([np.nan] * len(df))
        
        coverage = df["ebit"] / int_exp
        
        mask_cov = coverage < min_interest_coverage
        mask_cov = mask_cov.fillna(False)
        df.loc[mask_cov, "_exclude"] = True
        df.loc[mask_cov, "_exclude_reason"] += "Coverage; "
        excluded_cov = mask_cov.sum()
    
    # === Filtrer ===
    df_filtered = df[~df["_exclude"]].copy()
    
    # Nettoyer colonnes temporaires
    temp_cols = [c for c in df_filtered.columns if c.startswith("_")]
    df_filtered = df_filtered.drop(columns=temp_cols, errors="ignore")
    
    # === Logging ===
    final_count = len(df_filtered)
    excluded_total = initial_count - final_count
    
    if verbose:
        logger.info(
            f"Hard filters: {excluded_total}/{initial_count} exclus "
            f"({final_count} restants)"
        )
        if excluded_total > 0:
            logger.debug(f"  - D/E > {max_debt_equity}: {excluded_de}")
            logger.debug(f"  - ND/EBITDA > {max_debt_ebitda}: {excluded_nd}")
            logger.debug(f"  - Coverage < {min_interest_coverage}: {excluded_cov}")
    
    return df_filtered


def check_hard_filters_single(
    total_debt: float,
    equity: float,
    ebit: float,
    interest_expense: float,
    cash: float = 0,
) -> Dict[str, any]:
    """
    Vérifie les hard filters pour un seul titre.
    
    Returns:
        Dict avec should_exclude (bool) et détails.
    """
    # Calculs
    de_ratio = total_debt / equity if equity > 0 else float("inf")
    ebitda = ebit * 1.2
    net_debt = total_debt - cash
    nd_ebitda = net_debt / ebitda if ebitda > 0 else float("inf")
    coverage = ebit / abs(interest_expense) if interest_expense != 0 else float("inf")
    
    # Checks
    checks = {
        "de_ok": de_ratio <= HARD_FILTERS["max_debt_equity"],
        "nd_ebitda_ok": nd_ebitda <= HARD_FILTERS["max_debt_ebitda"],
        "coverage_ok": coverage >= HARD_FILTERS["min_interest_coverage"],
    }
    
    reasons = []
    if not checks["de_ok"]:
        reasons.append(f"D/E={de_ratio:.1f}")
    if not checks["nd_ebitda_ok"]:
        reasons.append(f"ND/EBITDA={nd_ebitda:.1f}")
    if not checks["coverage_ok"]:
        reasons.append(f"Coverage={coverage:.1f}")
    
    return {
        "should_exclude": not all(checks.values()),
        "checks": checks,
        "reasons": reasons,
        "metrics": {
            "de_ratio": round(de_ratio, 2) if de_ratio != float("inf") else None,
            "nd_ebitda": round(nd_ebitda, 2) if nd_ebitda != float("inf") else None,
            "coverage": round(coverage, 2) if coverage != float("inf") else None,
        },
    }
