"""SmartMoney v2.3 — Look-Ahead Filter

Évite le biais de look-ahead en filtrant les données
non encore publiées à la date de backtest.

LIMITATION DOCUMENTÉE:
- On suppose publication 60 jours après fin d'année fiscale (31/12)
- Les fiscal years non-calendaires ne sont pas gérés parfaitement
- C'est une RÉDUCTION du biais, pas une élimination complète

Date: Décembre 2025
"""

import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import LOOK_AHEAD
except ImportError:
    LOOK_AHEAD = {
        "publication_lag_days": 60,
        "quarterly_lag_days": 45,
    }

logger = logging.getLogger(__name__)


def filter_by_publication_date(
    fundamentals: pd.DataFrame,
    as_of_date: str,
    publication_lag_days: Optional[int] = None,
    year_column: str = "year",
    fiscal_year_end_month: int = 12,
    fiscal_year_end_day: int = 31,
) -> pd.DataFrame:
    """
    Filtre les données non encore publiées à as_of_date.
    
    Hypothèse: données annuelles publiées X jours après fin d'exercice fiscal.
    
    Args:
        fundamentals: DataFrame avec colonne 'year' (ou year_column)
        as_of_date: Date de référence (format YYYY-MM-DD ou datetime)
        publication_lag_days: Délai de publication. Défaut: config (60j)
        year_column: Nom de la colonne année
        fiscal_year_end_month: Mois de fin d'exercice (défaut: 12 = décembre)
        fiscal_year_end_day: Jour de fin d'exercice (défaut: 31)
    
    Returns:
        DataFrame avec seulement les données "publiées" à as_of_date.
    
    Raises:
        ValueError: Si aucune donnée n'est disponible avant as_of_date.
    
    Example:
        >>> df_valid = filter_by_publication_date(
        ...     fundamentals, 
        ...     as_of_date="2023-03-15"
        ... )
        >>> # Retourne données jusqu'à 2022 (pub ~fin février 2023)
    """
    lag_days = publication_lag_days or LOOK_AHEAD["publication_lag_days"]
    
    # Parser la date
    if isinstance(as_of_date, str):
        as_of = pd.to_datetime(as_of_date)
    else:
        as_of = pd.to_datetime(as_of_date)
    
    # Date limite de publication
    cutoff = as_of - timedelta(days=lag_days)
    
    df = fundamentals.copy()
    
    # Vérifier que la colonne année existe
    if year_column not in df.columns:
        raise ValueError(f"Colonne '{year_column}' non trouvée")
    
    # Calculer la date de publication estimée pour chaque année
    # fiscal_year_end = 31/12/year, publication = fiscal_year_end + lag
    df["_fiscal_year_end"] = pd.to_datetime(
        df[year_column].astype(str) + 
        f"-{fiscal_year_end_month:02d}-{fiscal_year_end_day:02d}"
    )
    df["_publication_date"] = df["_fiscal_year_end"] + timedelta(days=lag_days)
    
    # Filtrer
    mask = df["_publication_date"] <= cutoff
    df_filtered = df[mask].copy()
    
    # Nettoyer
    df_filtered = df_filtered.drop(
        columns=["_fiscal_year_end", "_publication_date"], 
        errors="ignore"
    )
    
    # Vérification
    if len(df_filtered) == 0:
        raise ValueError(
            f"Aucune donnée publiée avant {cutoff.date()} "
            f"(as_of={as_of.date()}, lag={lag_days}j)"
        )
    
    years_available = sorted(df_filtered[year_column].unique())
    logger.debug(
        f"Look-ahead filter: {len(df_filtered)}/{len(df)} lignes "
        f"(années: {years_available[0]}-{years_available[-1]})"
    )
    
    return df_filtered


def validate_no_look_ahead(
    fundamentals: pd.DataFrame,
    backtest_date: str,
    publication_lag_days: Optional[int] = None,
    year_column: str = "year",
) -> bool:
    """
    Valide qu'il n'y a pas de look-ahead bias dans les données.
    
    Args:
        fundamentals: DataFrame avec données fondamentales
        backtest_date: Date du backtest
        publication_lag_days: Délai de publication
        year_column: Nom de la colonne année
    
    Returns:
        True si OK (pas de look-ahead), False sinon.
    """
    lag_days = publication_lag_days or LOOK_AHEAD["publication_lag_days"]
    
    backtest_dt = pd.to_datetime(backtest_date)
    cutoff = backtest_dt - timedelta(days=lag_days)
    
    # Dernière année dans les données
    last_year = fundamentals[year_column].max()
    
    # Date de publication de cette année
    last_pub = pd.to_datetime(f"{int(last_year)}-12-31") + timedelta(days=lag_days)
    
    is_valid = last_pub <= cutoff
    
    if not is_valid:
        logger.warning(
            f"Look-ahead détecté: données {last_year} publiées ~{last_pub.date()}, "
            f"mais backtest à {backtest_dt.date()} (cutoff: {cutoff.date()})"
        )
    
    return is_valid


def get_latest_available_year(
    as_of_date: str,
    publication_lag_days: Optional[int] = None,
    fiscal_year_end_month: int = 12,
) -> int:
    """
    Retourne la dernière année fiscale dont les données sont disponibles.
    
    Example:
        >>> get_latest_available_year("2024-02-15")
        2022  # 2023 pas encore publié (60j après 31/12/2023 = fin février)
        
        >>> get_latest_available_year("2024-04-01")
        2023  # 2023 publié fin février
    """
    lag_days = publication_lag_days or LOOK_AHEAD["publication_lag_days"]
    as_of = pd.to_datetime(as_of_date)
    
    # Remonter année par année jusqu'à trouver une publication valide
    for year in range(as_of.year, as_of.year - 5, -1):
        pub_date = pd.to_datetime(
            f"{year}-{fiscal_year_end_month:02d}-31"
        ) + timedelta(days=lag_days)
        
        if pub_date <= as_of:
            return year
    
    return as_of.year - 2  # Fallback conservateur
