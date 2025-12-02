"""SmartMoney v2.3.1 — Tests Buffett Overlay

Tests pour:
- Configuration Buffett (BUFFETT_FILTERS, BUFFETT_SCORING, BUFFETT_PORTFOLIO)
- Filtres Buffett (apply_buffett_filters, compute_buffett_features)
- Score Buffett (calculate_buffett_score, _score_moat, _score_cash_quality)
- Intégration dans engine_v23

Lancer avec: pytest tests/test_buffett.py -v

Date: Décembre 2025
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Ajouter le repo au path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_universe_buffett():
    """Univers de test avec différents profils Buffett."""
    return pd.DataFrame({
        "symbol": ["QUALITY", "MEDIOCRE", "RISKY", "YOUNG", "BIOTECH"],
        "company": ["Quality Corp", "Mediocre Inc", "Risky Ltd", "Young Co", "Biotech SA"],
        "sector": ["Consumer Staples", "Industrials", "Financials", "Technology", "Healthcare"],
        "industry": ["Beverages", "Machinery", "Banks", "Software", "Biotechnology"],
        
        # Historique
        "years_of_data": [12, 8, 10, 4, 10],
        "loss_years_count": [0, 2, 5, 1, 3],
        
        # Rentabilité
        "roic_avg": [0.18, 0.09, 0.05, 0.12, 0.02],
        "roe_avg": [0.22, 0.11, 0.06, 0.15, 0.03],
        "roe": [0.20, 0.10, 0.05, 0.14, 0.02],
        
        # Stabilité
        "margin_stability": [0.85, 0.60, 0.30, 0.70, 0.20],
        
        # Cash
        "net_income": [5e9, 1e9, 500e6, 200e6, -100e6],
        "operating_cash_flow": [6e9, 800e6, 400e6, 250e6, -50e6],
        "fcf": [5.5e9, 700e6, 300e6, 180e6, -80e6],
        "total_assets": [50e9, 20e9, 30e9, 5e9, 10e9],
        
        # Levier
        "debt_equity": [0.5, 1.5, 4.0, 0.8, 2.5],
        "interest_coverage": [20, 5, 1.5, 8, 0.5],
        "current_ratio": [1.8, 1.2, 0.8, 2.0, 0.6],
        
        # Discipline capital
        "capital_discipline": [0.85, 0.50, 0.30, 0.60, 0.20],
        
        # Scores existants (pour composite)
        "score_value": [0.75, 0.50, 0.40, 0.60, 0.30],
        "score_quality": [0.80, 0.55, 0.35, 0.65, 0.25],
        "score_risk": [0.90, 0.60, 0.20, 0.70, 0.15],
    })


@pytest.fixture
def buffett_stock():
    """Un titre type Buffett (haute qualité)."""
    return pd.DataFrame({
        "symbol": ["BRK"],
        "years_of_data": [50],
        "loss_years_count": [0],
        "industry": ["Insurance"],
        "sector": ["Financials"],
        "roic_avg": [0.15],
        "roe_avg": [0.18],
        "margin_stability": [0.90],
        "net_income": [100e9],
        "operating_cash_flow": [120e9],
        "fcf": [110e9],
        "total_assets": [1000e9],
        "score_value": [0.70],
        "score_risk": [0.85],
        "capital_discipline": [0.90],
    })


@pytest.fixture
def speculative_stock():
    """Un titre spéculatif (doit être exclu)."""
    return pd.DataFrame({
        "symbol": ["SPAC"],
        "years_of_data": [2],
        "loss_years_count": [2],
        "industry": ["Blank Checks"],
        "sector": ["Financials"],
        "roic_avg": [-0.05],
        "roe_avg": [-0.10],
        "margin_stability": [0.10],
        "net_income": [-50e6],
        "operating_cash_flow": [-30e6],
        "fcf": [-40e6],
        "total_assets": [500e6],
        "score_value": [0.30],
        "score_risk": [0.10],
        "capital_discipline": [0.20],
    })


# =============================================================================
# TESTS CONFIG BUFFETT
# =============================================================================

class TestConfigBuffett:
    """Tests de la configuration Buffett v2.3.1."""
    
    def test_buffett_filters_exists(self):
        """BUFFETT_FILTERS doit exister dans config_v23."""
        from config_v23 import BUFFETT_FILTERS
        
        assert BUFFETT_FILTERS is not None
        assert isinstance(BUFFETT_FILTERS, dict)
    
    def test_buffett_filters_core_fields(self):
        """Les champs CORE doivent être présents."""
        from config_v23 import BUFFETT_FILTERS
        
        assert "min_history_years" in BUFFETT_FILTERS
        assert "max_loss_years" in BUFFETT_FILTERS
        assert "excluded_industries" in BUFFETT_FILTERS
    
    def test_buffett_filters_values_reasonable(self):
        """Les valeurs des filtres doivent être raisonnables."""
        from config_v23 import BUFFETT_FILTERS
        
        # Historique entre 5 et 15 ans
        assert 5 <= BUFFETT_FILTERS["min_history_years"] <= 15
        
        # Max pertes entre 2 et 5
        assert 2 <= BUFFETT_FILTERS["max_loss_years"] <= 5
        
        # Biotech doit être exclu
        assert "Biotechnology" in BUFFETT_FILTERS["excluded_industries"]
    
    def test_buffett_scoring_weights_sum(self):
        """Les poids quality + valuation doivent sommer à 1.0."""
        from config_v23 import BUFFETT_SCORING
        
        total = BUFFETT_SCORING["quality_weight"] + BUFFETT_SCORING["valuation_weight"]
        assert abs(total - 1.0) < 0.001, f"Somme = {total}, attendu 1.0"
    
    def test_buffett_scoring_quality_dominant(self):
        """La qualité doit dominer (> 50%)."""
        from config_v23 import BUFFETT_SCORING
        
        assert BUFFETT_SCORING["quality_weight"] > 0.50
    
    def test_buffett_portfolio_constraints(self):
        """Les contraintes portfolio doivent être cohérentes."""
        from config_v23 import BUFFETT_PORTFOLIO
        
        assert BUFFETT_PORTFOLIO["min_positions"] < BUFFETT_PORTFOLIO["max_positions"]
        assert BUFFETT_PORTFOLIO["max_weight"] <= 0.25  # Pas trop concentré
        assert BUFFETT_PORTFOLIO["rebal_freq"] == "A"  # Annuel


# =============================================================================
# TESTS BUFFETT FILTERS
# =============================================================================

class TestBuffettFilters:
    """Tests des filtres Buffett."""
    
    def test_excludes_short_history(self, sample_universe_buffett):
        """Exclut les titres avec historique < 7 ans."""
        from src.filters.buffett_filters import apply_buffett_filters
        
        filtered, rejected = apply_buffett_filters(sample_universe_buffett, verbose=False)
        
        # YOUNG a seulement 4 ans d'historique
        assert "YOUNG" not in filtered["symbol"].values
        assert rejected.get("history_insufficient", 0) >= 1
    
    def test_excludes_chronic_losses(self, sample_universe_buffett):
        """Exclut les titres avec > 3 années de pertes."""
        from src.filters.buffett_filters import apply_buffett_filters
        
        filtered, rejected = apply_buffett_filters(sample_universe_buffett, verbose=False)
        
        # RISKY a 5 années de pertes
        assert "RISKY" not in filtered["symbol"].values
        assert rejected.get("chronic_losses", 0) >= 1
    
    def test_excludes_biotech(self, sample_universe_buffett):
        """Exclut les biotechs."""
        from src.filters.buffett_filters import apply_buffett_filters
        
        filtered, rejected = apply_buffett_filters(sample_universe_buffett, verbose=False)
        
        # BIOTECH est dans l'industrie exclue
        assert "BIOTECH" not in filtered["symbol"].values
        assert rejected.get("excluded_industry", 0) >= 1
    
    def test_keeps_quality_stocks(self, sample_universe_buffett):
        """Garde les titres de qualité."""
        from src.filters.buffett_filters import apply_buffett_filters
        
        filtered, rejected = apply_buffett_filters(sample_universe_buffett, verbose=False)
        
        # QUALITY passe tous les filtres
        assert "QUALITY" in filtered["symbol"].values
    
    def test_buffett_stock_passes(self, buffett_stock):
        """Un titre type Buffett passe les filtres."""
        from src.filters.buffett_filters import apply_buffett_filters
        
        filtered, rejected = apply_buffett_filters(buffett_stock, verbose=False)
        
        assert len(filtered) == 1
        assert filtered.iloc[0]["symbol"] == "BRK"
    
    def test_speculative_stock_excluded(self, speculative_stock):
        """Un titre spéculatif est exclu."""
        from src.filters.buffett_filters import apply_buffett_filters
        
        filtered, rejected = apply_buffett_filters(speculative_stock, verbose=False)
        
        assert len(filtered) == 0


class TestBuffettFeatures:
    """Tests du calcul des features Buffett."""
    
    def test_compute_accruals(self, sample_universe_buffett):
        """Calcule correctement les accruals."""
        from src.filters.buffett_filters import compute_buffett_features
        
        df = compute_buffett_features(sample_universe_buffett)
        
        assert "accruals" in df.columns
        assert df["accruals"].notna().sum() > 0
        
        # Accruals = (NI - CFO) / Assets
        # Pour QUALITY: (5e9 - 6e9) / 50e9 = -0.02
        quality_accruals = df[df["symbol"] == "QUALITY"]["accruals"].iloc[0]
        assert -0.05 < quality_accruals < 0.05
    
    def test_compute_fcf_ni_ratio(self, sample_universe_buffett):
        """Calcule correctement le ratio FCF/NI."""
        from src.filters.buffett_filters import compute_buffett_features
        
        df = compute_buffett_features(sample_universe_buffett)
        
        assert "fcf_ni_ratio" in df.columns
        assert df["fcf_ni_ratio"].notna().sum() > 0
        
        # Pour QUALITY: 5.5e9 / 5e9 = 1.1
        quality_ratio = df[df["symbol"] == "QUALITY"]["fcf_ni_ratio"].iloc[0]
        assert 1.0 < quality_ratio < 1.5
    
    def test_accruals_winsorized(self, sample_universe_buffett):
        """Les accruals sont winsorisés entre -0.5 et 0.5."""
        from src.filters.buffett_filters import compute_buffett_features
        
        df = compute_buffett_features(sample_universe_buffett)
        
        assert df["accruals"].min() >= -0.5
        assert df["accruals"].max() <= 0.5
    
    def test_fcf_ni_winsorized(self, sample_universe_buffett):
        """Le ratio FCF/NI est winsorisé entre -2 et 3."""
        from src.filters.buffett_filters import compute_buffett_features
        
        df = compute_buffett_features(sample_universe_buffett)
        
        valid = df["fcf_ni_ratio"].dropna()
        assert valid.min() >= -2
        assert valid.max() <= 3


class TestCheckBuffettEligibility:
    """Tests de la vérification d'éligibilité individuelle."""
    
    def test_eligible_stock(self, buffett_stock):
        """Un titre éligible retourne True."""
        from src.filters.buffett_filters import check_buffett_eligibility
        
        row = buffett_stock.iloc[0]
        eligible, reasons = check_buffett_eligibility(row)
        
        assert eligible == True
        assert len(reasons) == 0
    
    def test_ineligible_stock_with_reasons(self, speculative_stock):
        """Un titre non éligible retourne les raisons."""
        from src.filters.buffett_filters import check_buffett_eligibility
        
        row = speculative_stock.iloc[0]
        eligible, reasons = check_buffett_eligibility(row)
        
        assert eligible == False
        assert len(reasons) >= 1


# =============================================================================
# TESTS BUFFETT SCORE
# =============================================================================

class TestBuffettScore:
    """Tests du calcul du score Buffett."""
    
    def test_score_buffett_calculated(self, sample_universe_buffett):
        """Le score Buffett est calculé."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        assert "score_buffett" in df.columns
        assert df["score_buffett"].notna().all()
    
    def test_score_buffett_range(self, sample_universe_buffett):
        """Le score Buffett est dans [0, 1]."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        assert df["score_buffett"].min() >= 0
        assert df["score_buffett"].max() <= 1
    
    def test_quality_stock_high_score(self, sample_universe_buffett):
        """Un titre de qualité a un score élevé."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        quality_score = df[df["symbol"] == "QUALITY"]["score_buffett"].iloc[0]
        mediocre_score = df[df["symbol"] == "MEDIOCRE"]["score_buffett"].iloc[0]
        
        assert quality_score > mediocre_score
    
    def test_sub_scores_calculated(self, sample_universe_buffett):
        """Les sous-scores sont calculés."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        assert "score_quality_buffett" in df.columns
        assert "score_valo_buffett" in df.columns
        assert "score_moat_buffett" in df.columns
        assert "score_cash_buffett" in df.columns
    
    def test_ranking_calculated(self, sample_universe_buffett):
        """Le ranking Buffett est calculé."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        assert "rank_buffett_v2" in df.columns
        
        # Le meilleur score = rang 1
        best = df.loc[df["score_buffett"].idxmax()]
        assert best["rank_buffett_v2"] == 1
    
    def test_score_independent_of_composite(self, sample_universe_buffett):
        """Le score Buffett est indépendant du composite."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score, calculate_composite_score
        
        df = compute_buffett_features(sample_universe_buffett)
        
        # Ajouter les scores de signaux pour le composite
        df["score_sm"] = 0.5
        df["score_insider"] = 0.5
        df["score_momentum"] = 0.5
        
        df = calculate_composite_score(df)
        df = calculate_buffett_score(df)
        
        # Les deux colonnes existent indépendamment
        assert "score_composite" in df.columns
        assert "score_buffett" in df.columns
        
        # Elles ne sont pas identiques
        assert not (df["score_composite"] == df["score_buffett"]).all()


class TestMoatScore:
    """Tests du score Moat."""
    
    def test_high_roic_high_score(self, sample_universe_buffett):
        """Un ROIC élevé donne un score moat élevé."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        quality_moat = df[df["symbol"] == "QUALITY"]["score_moat_buffett"].iloc[0]
        risky_moat = df[df["symbol"] == "RISKY"]["score_moat_buffett"].iloc[0]
        
        assert quality_moat > risky_moat


class TestCashQualityScore:
    """Tests du score Cash Quality."""
    
    def test_high_fcf_ni_high_score(self, sample_universe_buffett):
        """Un ratio FCF/NI > 1 donne un bon score cash."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        quality_cash = df[df["symbol"] == "QUALITY"]["score_cash_buffett"].iloc[0]
        
        # QUALITY a FCF/NI > 1 donc score élevé
        assert quality_cash > 0.5


# =============================================================================
# TESTS INTÉGRATION
# =============================================================================

class TestBuffettIntegration:
    """Tests d'intégration du pipeline Buffett."""
    
    def test_full_buffett_pipeline(self, sample_universe_buffett):
        """Test du pipeline complet Buffett."""
        from src.filters.buffett_filters import (
            compute_buffett_features,
            apply_buffett_filters,
            get_buffett_universe_stats,
        )
        from src.scoring.composite import calculate_buffett_score
        
        # 1. Features
        df = compute_buffett_features(sample_universe_buffett)
        assert "accruals" in df.columns
        assert "fcf_ni_ratio" in df.columns
        
        # 2. Score
        df = calculate_buffett_score(df)
        assert "score_buffett" in df.columns
        
        # 3. Filtres
        df_filtered, rejected = apply_buffett_filters(df, verbose=False)
        assert len(df_filtered) < len(df)
        
        # 4. Stats
        stats = get_buffett_universe_stats(df_filtered)
        assert "total_tickers" in stats
    
    def test_in_buffett_universe_flag(self, sample_universe_buffett):
        """Le flag in_buffett_universe est correctement calculé."""
        from src.filters.buffett_filters import (
            compute_buffett_features,
            apply_buffett_filters,
        )
        from src.scoring.composite import calculate_buffett_score
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        # Simuler ce que fait engine_v23
        df_buffett, _ = apply_buffett_filters(df.copy(), verbose=False)
        df["in_buffett_universe"] = df.index.isin(df_buffett.index)
        
        assert "in_buffett_universe" in df.columns
        assert df["in_buffett_universe"].dtype == bool
        
        # QUALITY doit être dans l'univers Buffett
        assert df[df["symbol"] == "QUALITY"]["in_buffett_universe"].iloc[0] == True
        
        # YOUNG ne doit pas être dans l'univers Buffett (historique < 7 ans)
        assert df[df["symbol"] == "YOUNG"]["in_buffett_universe"].iloc[0] == False


class TestGetBuffettScoreBreakdown:
    """Tests de la fonction d'analyse détaillée."""
    
    def test_breakdown_returns_correct_columns(self, sample_universe_buffett):
        """Le breakdown retourne les bonnes colonnes."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score, get_buffett_score_breakdown
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        breakdown = get_buffett_score_breakdown(df)
        
        assert "symbol" in breakdown.columns
        assert "score_buffett" in breakdown.columns
        assert "score_quality_buffett" in breakdown.columns
    
    def test_breakdown_sorted_by_score(self, sample_universe_buffett):
        """Le breakdown est trié par score décroissant."""
        from src.filters.buffett_filters import compute_buffett_features
        from src.scoring.composite import calculate_buffett_score, get_buffett_score_breakdown
        
        df = compute_buffett_features(sample_universe_buffett)
        df = calculate_buffett_score(df)
        
        breakdown = get_buffett_score_breakdown(df)
        
        # Vérifie que les scores sont décroissants
        scores = breakdown["score_buffett"].tolist()
        assert scores == sorted(scores, reverse=True)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
