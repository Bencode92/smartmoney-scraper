"""SmartMoney v2.3 — Data Validator

Valide et nettoie les données avant scoring:
- Vérifie les champs obligatoires
- Applique des bornes raisonnables
- Winsorise les outliers
- Log les anomalies

Date: Décembre 2025
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from config_v23 import DATA_BOUNDS, REQUIRED_FIELDS
except ImportError:
    DATA_BOUNDS = {
        "revenue": (0, 1e13),
        "net_income": (-1e12, 1e12),
        "ebit": (-1e12, 1e12),
        "equity": (-1e12, 5e12),
        "total_debt": (0, 5e12),
        "market_cap": (1e8, 5e13),
    }
    REQUIRED_FIELDS = ["revenue", "ebit", "net_income", "equity", "total_debt"]

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Résultat de validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cleaned_data: Optional[pd.Series] = None


class DataValidator:
    """
    Validateur de données fondamentales.
    
    Vérifie:
    - Présence des champs obligatoires
    - Valeurs dans des bornes raisonnables
    - Cohérence logique des données
    
    Example:
        >>> validator = DataValidator()
        >>> result = validator.validate_row(row, "AAPL")
        >>> if result.is_valid:
        ...     process(result.cleaned_data)
    """
    
    # Champs optionnels mais préférables
    PREFERRED_FIELDS: List[str] = [
        "fcf",
        "cash",
        "interest_expense",
        "shares_outstanding",
    ]
    
    def __init__(
        self,
        required_fields: Optional[List[str]] = None,
        bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        winsorize_outliers: bool = True,
    ):
        """
        Args:
            required_fields: Champs obligatoires (override défaut)
            bounds: Bornes par métrique (override défaut)
            winsorize_outliers: Si True, winsorise au lieu de rejeter
        """
        self.required_fields = required_fields or REQUIRED_FIELDS
        self.bounds = {**DATA_BOUNDS, **(bounds or {})}
        self.winsorize_outliers = winsorize_outliers
    
    def validate_row(
        self,
        row: pd.Series,
        ticker: str = "UNKNOWN",
    ) -> ValidationResult:
        """
        Valide une ligne de données.
        
        Args:
            row: Série pandas avec les métriques
            ticker: Symbole pour les logs
        
        Returns:
            ValidationResult avec is_valid, errors, warnings, cleaned_data
        """
        errors = []
        warnings = []
        cleaned = row.copy()
        
        # === 1. Champs obligatoires ===
        for field in self.required_fields:
            if field not in row:
                errors.append(f"Champ manquant: {field}")
            elif pd.isna(row[field]):
                errors.append(f"Valeur NaN: {field}")
        
        if errors:
            return ValidationResult(
                is_valid=False,
                errors=[f"{ticker}: {e}" for e in errors],
            )
        
        # === 2. Champs préférables ===
        for field in self.PREFERRED_FIELDS:
            if field not in row or pd.isna(row.get(field)):
                warnings.append(f"Champ préférable manquant: {field}")
        
        # === 3. Bornes ===
        for field, (lo, hi) in self.bounds.items():
            if field not in row or pd.isna(row.get(field)):
                continue
            
            val = row[field]
            
            if val < lo or val > hi:
                warnings.append(
                    f"{field}={val:,.0f} hors bornes [{lo:,.0f}, {hi:,.0f}]"
                )
                
                if self.winsorize_outliers:
                    cleaned[field] = np.clip(val, lo, hi)
        
        # === 4. Cohérence logique ===
        coherence_warnings = self._check_coherence(cleaned, ticker)
        warnings.extend(coherence_warnings)
        
        # Log warnings (seulement debug)
        for w in warnings:
            logger.debug(f"{ticker}: {w}")
        
        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[f"{ticker}: {w}" for w in warnings],
            cleaned_data=cleaned,
        )
    
    def _check_coherence(self, row: pd.Series, ticker: str) -> List[str]:
        """Vérifie la cohérence logique des données."""
        warnings = []
        
        # Marge nette > 100% ?
        if "revenue" in row and "net_income" in row:
            rev = row.get("revenue")
            ni = row.get("net_income")
            if rev and not pd.isna(rev) and rev > 0:
                if ni and not pd.isna(ni):
                    margin = ni / rev
                    if abs(margin) > 1:
                        warnings.append(f"Marge nette {margin*100:.0f}% > 100%")
        
        # D/E extrême ?
        if "total_debt" in row and "equity" in row:
            debt = row.get("total_debt")
            eq = row.get("equity")
            if eq and not pd.isna(eq) and eq > 0:
                if debt and not pd.isna(debt):
                    de = debt / eq
                    if de > 10:
                        warnings.append(f"D/E = {de:.1f} très élevé")
        
        # FCF >> Net Income ?
        if "fcf" in row and "net_income" in row:
            fcf = row.get("fcf")
            ni = row.get("net_income")
            if ni and not pd.isna(ni) and ni > 0:
                if fcf and not pd.isna(fcf):
                    fcf_ratio = fcf / ni
                    if fcf_ratio > 3:
                        warnings.append(f"FCF/NI = {fcf_ratio:.1f} suspect")
        
        return warnings
    
    def validate_dataframe(
        self,
        df: pd.DataFrame,
        ticker: str = "UNKNOWN",
        min_valid_rows: int = 5,
    ) -> Tuple[bool, pd.DataFrame, List[str]]:
        """
        Valide un DataFrame complet (historique).
        
        Args:
            df: DataFrame avec plusieurs années
            ticker: Symbole pour les logs
            min_valid_rows: Minimum de lignes valides requises
        
        Returns:
            Tuple (is_valid, cleaned_df, all_warnings)
        """
        valid_rows = []
        all_warnings = []
        
        for idx, row in df.iterrows():
            result = self.validate_row(row, ticker)
            
            if result.is_valid:
                valid_rows.append(result.cleaned_data)
            
            all_warnings.extend(result.warnings)
        
        n_valid = len(valid_rows)
        
        if n_valid < min_valid_rows:
            logger.error(
                f"{ticker}: seulement {n_valid} lignes valides "
                f"(minimum: {min_valid_rows})"
            )
            return False, pd.DataFrame(), all_warnings
        
        cleaned_df = pd.DataFrame(valid_rows)
        
        logger.debug(f"{ticker}: {n_valid}/{len(df)} lignes valides")
        
        return True, cleaned_df, all_warnings


def validate_universe(
    universe: pd.DataFrame,
    validator: Optional[DataValidator] = None,
) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    """
    Valide un univers complet de tickers.
    
    Args:
        universe: DataFrame avec une ligne par ticker
        validator: Instance de DataValidator (défaut: nouveau)
    
    Returns:
        Tuple (df_valid, warnings_by_ticker)
    """
    validator = validator or DataValidator()
    
    valid_rows = []
    warnings_dict = {}
    
    for idx, row in universe.iterrows():
        ticker = row.get("symbol", row.get("ticker", f"ROW_{idx}"))
        result = validator.validate_row(row, ticker)
        
        if result.is_valid:
            valid_rows.append(result.cleaned_data)
        
        if result.warnings:
            warnings_dict[ticker] = result.warnings
    
    df_valid = pd.DataFrame(valid_rows)
    
    logger.info(
        f"Validation univers: {len(df_valid)}/{len(universe)} tickers valides"
    )
    
    return df_valid, warnings_dict
