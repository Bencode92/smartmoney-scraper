"""SmartMoney v2.3.1 — Buffett Filters

Filtres spécifiques au mode Buffett:
- Historique minimum (7 ans = un cycle économique)
- Maximum d'années de pertes (3 sur 10)
- Industries exclues (Biotech, SPACs)
- Cercle de compétence (secteurs autorisés)

Usage:
    from src.filters.buffett_filters import apply_buffett_filters, compute_buffett_features
    
    df = compute_buffett_features(df)  # Calcule accruals, fcf_ni_ratio
    df_filtered, rejected = apply_buffett_filters(df)

Ordre d'appel recommandé dans le pipeline:
    1. liquidity_filters
    2. data_validator
    3. buffett_filters  <-- ICI
    4. hard_filters

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)

# Import config - fallback si import échoue
try:
    from config_v23 import BUFFETT_FILTERS
except ImportError:
    BUFFETT_FILTERS = {
        "min_history_years": 7,
        "max_loss_years": 3,
        "ideal_history_years": 10,
        "min_roe_avg": 0.10,
        "min_roic_avg": 0.08,
        "allowed_sectors": [],
        "excluded_industries": ["Biotechnology", "Blank Checks"],
    }


def apply_buffett_filters(
    df: pd.DataFrame,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Applique les filtres Buffett CORE (mode soft).
    
    Filtres appliqués:
    1. Historique minimum (7 ans)
    2. Maximum d'années de pertes (3)
    3. Industries exclues (Biotech, SPACs)
    
    Note: Les filtres PREFERENCES (ROE min, secteurs) ne sont PAS appliqués
    en mode soft - ils seront utilisés comme pénalités dans le scoring.
    
    Args:
        df: DataFrame univers avec colonnes optionnelles:
            - years_of_data: nombre d'années de données
            - loss_years_count: nombre d'années avec net_income < 0
            - industry: industrie du titre
        verbose: Afficher les statistiques de filtrage
    
    Returns:
        Tuple (DataFrame filtré, Dict des exclusions par raison)
    
    Example:
        >>> df_filtered, rejected = apply_buffett_filters(df)
        >>> print(f"Exclus: {sum(rejected.values())} titres")
    """
    initial = len(df)
    rejected: Dict[str, int] = {}
    
    if df.empty:
        logger.warning("DataFrame vide passé à apply_buffett_filters")
        return df, rejected
    
    # =========================================================================
    # FILTRE 1: Historique minimum (CORE)
    # =========================================================================
    min_years = BUFFETT_FILTERS.get("min_history_years", 7)
    
    if "years_of_data" in df.columns:
        mask = df["years_of_data"] >= min_years
        rejected["history_insufficient"] = (~mask).sum()
        df = df[mask].copy()
        
        if verbose and rejected["history_insufficient"] > 0:
            logger.debug(f"Historique < {min_years} ans: {rejected['history_insufficient']} exclus")
    
    # =========================================================================
    # FILTRE 2: Années de pertes (CORE)
    # =========================================================================
    max_loss = BUFFETT_FILTERS.get("max_loss_years", 3)
    
    if "loss_years_count" in df.columns:
        mask = df["loss_years_count"] <= max_loss
        rejected["chronic_losses"] = (~mask).sum()
        df = df[mask].copy()
        
        if verbose and rejected["chronic_losses"] > 0:
            logger.debug(f"Pertes > {max_loss} années: {rejected['chronic_losses']} exclus")
    
    # =========================================================================
    # FILTRE 3: Industries exclues (CORE - trop spéculatif)
    # =========================================================================
    excluded_industries = BUFFETT_FILTERS.get("excluded_industries", [])
    
    if excluded_industries and "industry" in df.columns:
        # Normaliser les noms pour comparaison
        df_industries = df["industry"].fillna("").str.strip().str.lower()
        excluded_lower = [ind.lower() for ind in excluded_industries]
        
        mask = ~df_industries.isin(excluded_lower)
        rejected["excluded_industry"] = (~mask).sum()
        df = df[mask].copy()
        
        if verbose and rejected["excluded_industry"] > 0:
            logger.debug(f"Industries exclues: {rejected['excluded_industry']} exclus")
    
    # =========================================================================
    # LOG FINAL
    # =========================================================================
    final = len(df)
    total_excluded = initial - final
    
    if verbose:
        print(f"\n   Filtres Buffett (soft): {initial} → {final} tickers")
        for reason, count in rejected.items():
            if count > 0:
                print(f"      ✗ {reason}: {count}")
        
        # Distribution secteurs post-filtre
        if "sector" in df.columns and len(df) > 0:
            top_sectors = df["sector"].value_counts().head(5)
            print(f"      Top secteurs restants: {dict(top_sectors)}")
    
    logger.info(f"Buffett filters: {initial} → {final} ({total_excluded} exclus)")
    
    return df, rejected


def compute_buffett_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les features Buffett manquantes.
    
    Features calculées:
    - accruals: (Net Income - CFO) / Total Assets
      → Mesure la qualité des bénéfices (bas = cash réel)
    - fcf_ni_ratio: FCF / Net Income
      → Conversion des profits en cash (> 1 = excellent)
    
    À appeler AVANT apply_buffett_filters et calculate_buffett_score.
    
    Args:
        df: DataFrame avec colonnes optionnelles:
            - net_income
            - operating_cash_flow (ou cfo, cash_flow_operating)
            - total_assets
            - fcf
    
    Returns:
        DataFrame avec colonnes ajoutées: accruals, fcf_ni_ratio
    
    Example:
        >>> df = compute_buffett_features(df)
        >>> print(df[["symbol", "accruals", "fcf_ni_ratio"]].head())
    """
    df = df.copy()
    
    # =========================================================================
    # ACCRUALS = (Net Income - CFO) / Total Assets
    # =========================================================================
    # Plus c'est bas, mieux c'est (bénéfices = cash réel)
    # Seuils typiques: < 5% excellent, > 15% suspect
    
    ni = df.get("net_income")
    cfo = _get_cfo(df)
    assets = df.get("total_assets")
    
    if ni is not None and cfo is not None and assets is not None:
        # Éviter division par zéro
        safe_assets = assets.replace(0, np.nan)
        
        accruals = (ni - cfo) / safe_assets
        
        # Winsorize pour éviter les outliers extrêmes
        df["accruals"] = accruals.clip(-0.5, 0.5)
        
        # Stats pour debug
        valid_count = df["accruals"].notna().sum()
        logger.debug(f"Accruals calculés: {valid_count}/{len(df)} valides")
    else:
        df["accruals"] = np.nan
        logger.debug("Accruals: colonnes manquantes (net_income, cfo, ou total_assets)")
    
    # =========================================================================
    # FCF / NET INCOME RATIO
    # =========================================================================
    # > 1 = excellent (génère plus de cash que de profit comptable)
    # < 0.5 = suspect (profits non convertis en cash)
    
    fcf = df.get("fcf")
    
    if fcf is not None and ni is not None:
        # Éviter division par zéro
        safe_ni = ni.replace(0, np.nan)
        
        fcf_ni = fcf / safe_ni
        
        # Remplacer inf par nan
        fcf_ni = fcf_ni.replace([np.inf, -np.inf], np.nan)
        
        # Winsorize (ratios extrêmes = données suspectes)
        df["fcf_ni_ratio"] = fcf_ni.clip(-2, 3)
        
        valid_count = df["fcf_ni_ratio"].notna().sum()
        logger.debug(f"FCF/NI ratio calculé: {valid_count}/{len(df)} valides")
    else:
        df["fcf_ni_ratio"] = np.nan
        logger.debug("FCF/NI ratio: colonnes manquantes (fcf ou net_income)")
    
    return df


def _get_cfo(df: pd.DataFrame) -> Optional[pd.Series]:
    """
    Récupère le Cash Flow from Operations avec fallback sur noms alternatifs.
    
    Les APIs financières utilisent différents noms pour cette métrique:
    - operating_cash_flow (Twelve Data)
    - cfo (convention commune)
    - netCashProvidedByOperatingActivities (SEC EDGAR)
    - cashFlowFromOperations
    - cash_flow_operating
    
    Args:
        df: DataFrame avec une des colonnes CFO
    
    Returns:
        Series du CFO ou None si non trouvé
    """
    cfo_columns = [
        "operating_cash_flow",
        "cfo",
        "netCashProvidedByOperatingActivities",
        "cashFlowFromOperations",
        "cash_flow_operating",
        "operatingCashFlow",
    ]
    
    for col in cfo_columns:
        if col in df.columns:
            logger.debug(f"CFO trouvé dans colonne: {col}")
            return df[col]
    
    logger.debug(f"CFO non trouvé. Colonnes disponibles: {list(df.columns)[:20]}...")
    return None


def check_buffett_eligibility(row: pd.Series) -> Tuple[bool, List[str]]:
    """
    Vérifie si un titre individuel passe les filtres Buffett.
    
    Utile pour le debug ou l'affichage dans le dashboard.
    
    Args:
        row: Série avec les données d'un titre
    
    Returns:
        Tuple (est_éligible, liste_des_raisons_d_exclusion)
    
    Example:
        >>> eligible, reasons = check_buffett_eligibility(df.iloc[0])
        >>> if not eligible:
        ...     print(f"Exclu pour: {reasons}")
    """
    reasons = []
    
    # Historique
    min_years = BUFFETT_FILTERS.get("min_history_years", 7)
    years = row.get("years_of_data", 0)
    if pd.notna(years) and years < min_years:
        reasons.append(f"historique={years}y < {min_years}y")
    
    # Pertes
    max_loss = BUFFETT_FILTERS.get("max_loss_years", 3)
    losses = row.get("loss_years_count", 0)
    if pd.notna(losses) and losses > max_loss:
        reasons.append(f"pertes={losses} > {max_loss}")
    
    # Industrie
    excluded = BUFFETT_FILTERS.get("excluded_industries", [])
    industry = str(row.get("industry", "")).strip().lower()
    excluded_lower = [ind.lower() for ind in excluded]
    if industry in excluded_lower:
        reasons.append(f"industrie={industry}")
    
    return len(reasons) == 0, reasons


def get_buffett_universe_stats(df: pd.DataFrame) -> Dict[str, any]:
    """
    Retourne des statistiques sur l'univers Buffett.
    
    Utile pour le monitoring et le dashboard.
    
    Args:
        df: DataFrame univers
    
    Returns:
        Dict avec statistiques
    """
    stats = {
        "total_tickers": len(df),
        "with_accruals": df["accruals"].notna().sum() if "accruals" in df.columns else 0,
        "with_fcf_ni": df["fcf_ni_ratio"].notna().sum() if "fcf_ni_ratio" in df.columns else 0,
    }
    
    # Accruals stats
    if "accruals" in df.columns:
        acc = df["accruals"].dropna()
        if len(acc) > 0:
            stats["accruals_mean"] = round(acc.mean(), 4)
            stats["accruals_median"] = round(acc.median(), 4)
            stats["accruals_low_pct"] = round((acc < 0.05).mean() * 100, 1)
    
    # FCF/NI stats
    if "fcf_ni_ratio" in df.columns:
        ratio = df["fcf_ni_ratio"].dropna()
        if len(ratio) > 0:
            stats["fcf_ni_mean"] = round(ratio.mean(), 2)
            stats["fcf_ni_above_1_pct"] = round((ratio > 1).mean() * 100, 1)
    
    # Secteurs
    if "sector" in df.columns:
        stats["sectors"] = df["sector"].value_counts().to_dict()
    
    return stats
