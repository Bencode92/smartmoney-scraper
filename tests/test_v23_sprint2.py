"""SmartMoney v2.3 — Tests Sprint 2 (Scoring)

Tests pour:
- Value Composite
- Quality Composite
- Risk Score (inversé)
- Composite final

Lancer avec: pytest tests/test_v23_sprint2.py -v
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def good_company():
    """Entreprise de qualité (style Buffett)."""
    return pd.Series({
        "symbol": "QUALITY",
        "sector": "Technology",
        "market_cap": 100e9,
        "fcf": 10e9,          # FCF yield = 10%
        "ebit": 15e9,
        "total_debt": 10e9,
        "equity": 50e9,        # D/E = 0.2
        "cash": 20e9,
        "interest_expense": 0.5e9,  # Coverage = 30
        "vol_30d": 20,
        "pe_ratio": 12,
        "revenue": 80e9,
        "net_income": 12e9,
    })


@pytest.fixture
def risky_company():
    """Entreprise risquée."""
    return pd.Series({
        "symbol": "RISKY",
        "sector": "Consumer Discretionary",
        "market_cap": 10e9,
        "fcf": -0.5e9,          # FCF négatif
        "ebit": 0.5e9,
        "total_debt": 15e9,
        "equity": 5e9,           # D/E = 3
        "cash": 1e9,
        "interest_expense": 0.8e9,  # Coverage = 0.625
        "vol_30d": 55,
        "pe_ratio": 35,
        "revenue": 20e9,
        "net_income": 0.3e9,
    })


@pytest.fixture
def sample_universe(good_company, risky_company):
    """Univers avec différents profils."""
    neutral = pd.Series({
        "symbol": "NEUTRAL",
        "sector": "Industrials",
        "market_cap": 30e9,
        "fcf": 1.5e9,
        "ebit": 3e9,
        "total_debt": 8e9,
        "equity": 15e9,
        "cash": 2e9,
        "interest_expense": 0.4e9,
        "vol_30d": 30,
        "pe_ratio": 18,
        "revenue": 40e9,
        "net_income": 2e9,
    })
    
    return pd.DataFrame([good_company, risky_company, neutral])


# =============================================================================
# TESTS VALUE COMPOSITE
# =============================================================================

class TestValueComposite:
    """Tests du scoring Value."""
    
    def test_high_fcf_yield_scores_well(self, good_company):
        """FCF yield élevé = score élevé."""
        from src.scoring.value_composite import ValueScorer
        
        scorer = ValueScorer()
        result = scorer.score(good_company)
        
        assert result.fcf_yield_score >= 0.75
        assert result.details["fcf_yield"] >= 8  # > 8%
    
    def test_negative_fcf_scores_low(self, risky_company):
        """FCF négatif = score bas."""
        from src.scoring.value_composite import ValueScorer
        
        scorer = ValueScorer()
        result = scorer.score(risky_company)
        
        assert result.fcf_yield_score <= 0.25
    
    def test_low_pe_scores_well(self, good_company):
        """P/E bas = MoS élevé."""
        from src.scoring.value_composite import ValueScorer
        
        scorer = ValueScorer()
        result = scorer.score(good_company)
        
        assert result.mos_score >= 0.5
    
    def test_score_value_dataframe(self, sample_universe):
        """Test sur DataFrame complet."""
        from src.scoring.value_composite import score_value
        
        df = score_value(sample_universe)
        
        assert "score_value" in df.columns
        assert df["score_value"].notna().all()
        
        # QUALITY doit avoir le meilleur score value
        quality_score = df[df["symbol"] == "QUALITY"]["score_value"].values[0]
        risky_score = df[df["symbol"] == "RISKY"]["score_value"].values[0]
        
        assert quality_score > risky_score


# =============================================================================
# TESTS QUALITY COMPOSITE
# =============================================================================

class TestQualityComposite:
    """Tests du scoring Quality."""
    
    def test_high_roic_scores_well(self, good_company):
        """ROIC élevé = score élevé."""
        from src.scoring.quality_composite import QualityScorer
        
        scorer = QualityScorer()
        result = scorer.score(good_company)
        
        # ROIC = EBIT * 0.75 / (equity + debt - cash)
        # = 15e9 * 0.75 / (50 + 10 - 20) = 11.25 / 40 = 28%
        assert result.roic_score >= 0.70
    
    def test_low_de_capital_discipline(self, good_company):
        """D/E bas = bonne discipline."""
        from src.scoring.quality_composite import QualityScorer
        
        scorer = QualityScorer()
        result = scorer.score(good_company)
        
        assert result.capital_discipline_score >= 0.50
    
    def test_score_quality_dataframe(self, sample_universe):
        """Test sur DataFrame complet."""
        from src.scoring.quality_composite import score_quality
        
        df = score_quality(sample_universe)
        
        assert "score_quality" in df.columns
        assert df["score_quality"].notna().all()


# =============================================================================
# TESTS RISK SCORE (INVERSÉ)
# =============================================================================

class TestRiskScore:
    """Tests du scoring Risk (inversé)."""
    
    def test_safe_company_high_score(self, good_company):
        """Entreprise sûre = score ÉLEVÉ (inversé)."""
        from src.scoring.risk_score import RiskScorer
        
        scorer = RiskScorer()
        result = scorer.score(good_company)
        
        # Score élevé = risque faible
        assert result.total >= 0.70
        assert result.leverage_score >= 0.80
        assert result.coverage_score >= 0.80
    
    def test_risky_company_low_score(self, risky_company):
        """Entreprise risquée = score BAS (inversé)."""
        from src.scoring.risk_score import RiskScorer
        
        scorer = RiskScorer()
        result = scorer.score(risky_company)
        
        # Score bas = risque élevé
        assert result.total <= 0.40
        assert result.leverage_score <= 0.30  # D/E = 3
    
    def test_volatility_scoring(self, good_company, risky_company):
        """Volatilité basse = score élevé."""
        from src.scoring.risk_score import RiskScorer
        
        scorer = RiskScorer()
        
        good_result = scorer.score(good_company)
        risky_result = scorer.score(risky_company)
        
        assert good_result.volatility_score > risky_result.volatility_score
    
    def test_score_risk_dataframe(self, sample_universe):
        """Test sur DataFrame complet."""
        from src.scoring.risk_score import score_risk
        
        df = score_risk(sample_universe)
        
        assert "score_risk" in df.columns
        assert df["score_risk"].notna().all()
        
        # QUALITY doit avoir le meilleur score risk (inversé)
        quality_score = df[df["symbol"] == "QUALITY"]["score_risk"].values[0]
        risky_score = df[df["symbol"] == "RISKY"]["score_risk"].values[0]
        
        assert quality_score > risky_score


# =============================================================================
# TESTS COMPOSITE
# =============================================================================

class TestComposite:
    """Tests du scoring composite."""
    
    def test_weights_validation(self):
        """Poids doivent sommer à 1."""
        from src.scoring.composite import CompositeScorer
        
        # Poids valides
        scorer = CompositeScorer()
        assert scorer is not None
        
        # Poids invalides (somme != 1)
        with pytest.raises(ValueError):
            CompositeScorer(weights={"a": 0.5, "b": 0.3})  # = 0.8
    
    def test_no_negative_weights(self):
        """Poids négatifs interdits."""
        from src.scoring.composite import CompositeScorer
        
        with pytest.raises(ValueError):
            CompositeScorer(weights={"a": 0.5, "b": 0.6, "c": -0.1})
    
    def test_buffett_score_calculated(self, sample_universe):
        """Buffett score = (value + quality + risk) / 3."""
        from src.scoring.composite import calculate_all_scores
        
        # Ajouter les scores mock pour smart_money, insider, momentum
        sample_universe["score_sm"] = 0.5
        sample_universe["score_insider"] = 0.5
        sample_universe["score_momentum"] = 0.5
        
        df = calculate_all_scores(sample_universe)
        
        assert "buffett_score" in df.columns
        assert "score_composite" in df.columns
        
        # Vérifier que buffett_score est bien la moyenne
        for _, row in df.iterrows():
            expected = (row["score_value"] + row["score_quality"] + row["score_risk"]) / 3
            assert abs(row["buffett_score"] - expected) < 0.01
    
    def test_quality_company_ranks_higher(self, sample_universe):
        """L'entreprise de qualité doit être mieux classée."""
        from src.scoring.composite import calculate_all_scores
        
        sample_universe["score_sm"] = 0.5
        sample_universe["score_insider"] = 0.5
        sample_universe["score_momentum"] = 0.5
        
        df = calculate_all_scores(sample_universe)
        
        quality_rank = df[df["symbol"] == "QUALITY"]["rank_composite"].values[0]
        risky_rank = df[df["symbol"] == "RISKY"]["rank_composite"].values[0]
        
        assert quality_rank < risky_rank  # Rank plus bas = meilleur


# =============================================================================
# TESTS D'INTÉGRATION
# =============================================================================

class TestIntegration:
    """Tests d'intégration du pipeline scoring."""
    
    def test_full_scoring_pipeline(self, sample_universe):
        """Test du pipeline complet de scoring."""
        from src.scoring.composite import calculate_all_scores
        
        # Ajouter les scores v2.2 existants
        sample_universe["score_sm"] = [0.8, 0.3, 0.5]
        sample_universe["score_insider"] = [0.7, 0.4, 0.5]
        sample_universe["score_momentum"] = [0.6, 0.5, 0.5]
        
        df = calculate_all_scores(sample_universe)
        
        # Vérifier toutes les colonnes présentes
        expected_cols = [
            "score_value", "score_quality", "score_risk",
            "score_composite", "buffett_score",
            "rank_composite",
        ]
        
        for col in expected_cols:
            assert col in df.columns, f"Colonne {col} manquante"
        
        # Vérifier que les scores sont dans [0, 1] (ou z-scores)
        for col in ["score_value", "score_quality", "score_risk", "buffett_score"]:
            assert df[col].min() >= 0, f"{col} min < 0"
            assert df[col].max() <= 1, f"{col} max > 1"
    
    def test_scoring_with_missing_data(self):
        """Test avec données manquantes."""
        from src.scoring.composite import calculate_all_scores
        
        # Données minimales avec NaN
        df = pd.DataFrame([{
            "symbol": "MINIMAL",
            "sector": "Unknown",
            "market_cap": 10e9,
            "ebit": 1e9,
            "equity": 5e9,
            "total_debt": 2e9,
            "revenue": 20e9,
            "net_income": 0.5e9,
            "score_sm": 0.5,
            "score_insider": 0.5,
            "score_momentum": 0.5,
        }])
        
        # Ne doit pas planter
        result = calculate_all_scores(df)
        
        assert len(result) == 1
        assert "score_composite" in result.columns


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
