"""
Tests pour valider la robustesse du scraper HedgeFollow.
"""
import pytest
import pandas as pd
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

# Ajouter le chemin du projet au PYTHONPATH
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hedgefollow.funds import scrape_top_funds, get_top_n_funds
from src.validators import DataValidator, ScrapingValidator
from src.utils.parsing import make_soup


# HTML de test simulant la structure HedgeFollow
MOCK_HTML_VALID = """
<html>
<body>
    <table class="funds-table">
        <thead>
            <tr>
                <th>Fund Manager</th>
                <th>AUM (Billions)</th>
                <th>3Y Performance</th>
                <th>Holdings</th>
                <th>Top 20 Concentration</th>
                <th>Turnover</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><a href="/funds/bridgewater">Bridgewater Associates</a></td>
                <td>$150.0B</td>
                <td>12.5%</td>
                <td>523</td>
                <td>45.2%</td>
                <td>25%</td>
            </tr>
            <tr>
                <td><a href="/funds/renaissance">Renaissance Technologies</a></td>
                <td>$130.0B</td>
                <td>35.8%</td>
                <td>3521</td>
                <td>15.3%</td>
                <td>95%</td>
            </tr>
            <tr>
                <td>Two Sigma Investments</td>
                <td>$78.0B</td>
                <td>18.2%</td>
                <td>1852</td>
                <td>22.1%</td>
                <td>65%</td>
            </tr>
            <tr>
                <td><a href="/funds/citadel">Citadel</a></td>
                <td>$65.0B</td>
                <td>24.3%</td>
                <td>456</td>
                <td>38.9%</td>
                <td>45%</td>
            </tr>
            <tr>
                <td>Millennium Management</td>
                <td>$60.5B</td>
                <td>15.7%</td>
                <td>2134</td>
                <td>18.6%</td>
                <td>78%</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

# HTML avec structure différente (fallback test)
MOCK_HTML_DIFFERENT = """
<html>
<body>
    <div id="content">
        <table>
            <tr>
                <th>Manager</th>
                <th>Assets</th>
                <th>Performance</th>
            </tr>
            <tr>
                <td>Test Fund 1</td>
                <td>10B</td>
                <td>5.5%</td>
            </tr>
            <tr>
                <td>Test Fund 2</td>
                <td>8B</td>
                <td>3.2%</td>
            </tr>
        </table>
    </div>
</body>
</html>
"""

# HTML invalide
MOCK_HTML_INVALID = """
<html>
<body>
    <p>No tables here</p>
</body>
</html>
"""


class TestDataValidator:
    """Tests pour le validateur de données."""
    
    def test_validate_funds_success(self):
        """Test validation réussie des fonds."""
        df = pd.DataFrame({
            'fund_id': ['fund1', 'fund2', 'fund3', 'fund4', 'fund5'],
            'name': ['Fund 1', 'Fund 2', 'Fund 3', 'Fund 4', 'Fund 5'],
            'aum_usd': [1e10, 2e10, 3e10, 4e10, 5e10],
            'num_holdings': [100, 200, 300, 400, 500]
        })
        
        assert DataValidator.validate_funds(df, min_funds=5) == True
    
    def test_validate_funds_not_enough(self):
        """Test échec si pas assez de fonds."""
        df = pd.DataFrame({
            'fund_id': ['fund1', 'fund2'],
            'name': ['Fund 1', 'Fund 2'],
            'aum_usd': [1e10, 2e10]
        })
        
        with pytest.raises(ValueError, match="Seulement 2 fonds trouvés"):
            DataValidator.validate_funds(df, min_funds=5)
    
    def test_validate_funds_missing_columns(self):
        """Test échec si colonnes manquantes."""
        df = pd.DataFrame({
            'name': ['Fund 1', 'Fund 2', 'Fund 3', 'Fund 4', 'Fund 5']
        })
        
        with pytest.raises(ValueError, match="Colonnes manquantes"):
            DataValidator.validate_funds(df)
    
    def test_validate_funds_duplicate_ids(self):
        """Test échec si IDs dupliqués."""
        df = pd.DataFrame({
            'fund_id': ['fund1', 'fund1', 'fund3', 'fund4', 'fund5'],
            'name': ['Fund 1', 'Fund 2', 'Fund 3', 'Fund 4', 'Fund 5'],
            'aum_usd': [1e10, 2e10, 3e10, 4e10, 5e10]
        })
        
        with pytest.raises(ValueError, match="Fund IDs dupliqués"):
            DataValidator.validate_funds(df)
    
    def test_validate_funds_negative_aum(self):
        """Test échec si AUM négatifs."""
        df = pd.DataFrame({
            'fund_id': ['fund1', 'fund2', 'fund3', 'fund4', 'fund5'],
            'name': ['Fund 1', 'Fund 2', 'Fund 3', 'Fund 4', 'Fund 5'],
            'aum_usd': [1e10, -2e10, 3e10, 4e10, 5e10]
        })
        
        with pytest.raises(ValueError, match="AUM négatifs"):
            DataValidator.validate_funds(df)


class TestScrapingValidator:
    """Tests pour le validateur de structure HTML."""
    
    def test_validate_html_structure_success(self):
        """Test validation réussie de structure HTML."""
        soup = make_soup(MOCK_HTML_VALID)
        
        assert ScrapingValidator.validate_html_structure(
            soup,
            {
                "table": "Tableau principal",
                "th": "Headers"
            }
        ) == True
    
    def test_validate_html_structure_missing_elements(self):
        """Test échec si éléments manquants."""
        soup = make_soup(MOCK_HTML_INVALID)
        
        with pytest.raises(ValueError, match="Structure HTML changée"):
            ScrapingValidator.validate_html_structure(
                soup,
                {
                    "table": "Tableau",
                    "thead": "Headers"
                }
            )
    
    def test_validate_table_headers_exact(self):
        """Test validation exacte des headers."""
        soup = make_soup(MOCK_HTML_VALID)
        table = soup.find("table")
        
        with pytest.raises(ValueError, match="Headers manquants"):
            ScrapingValidator.validate_table_headers(
                table,
                ["Fund Manager", "AUM", "Performance"],
                fuzzy=False
            )
    
    def test_validate_table_headers_fuzzy(self):
        """Test validation approximative des headers."""
        soup = make_soup(MOCK_HTML_VALID)
        table = soup.find("table")
        
        assert ScrapingValidator.validate_table_headers(
            table,
            ["fund", "aum", "performance"],
            fuzzy=True
        ) == True


class TestFundsScraper:
    """Tests pour le scraper de fonds."""
    
    @patch('src.hedgefollow.funds.fetch_html')
    def test_scrape_top_funds_success(self, mock_fetch):
        """Test scraping réussi avec HTML valide."""
        mock_fetch.return_value = MOCK_HTML_VALID
        
        df = scrape_top_funds()
        
        assert not df.empty
        assert len(df) == 5
        assert 'fund_id' in df.columns
        assert 'name' in df.columns
        assert 'aum_usd' in df.columns
        assert df.iloc[0]['name'] == 'Bridgewater Associates'
        assert df.iloc[0]['aum_usd'] == 150_000_000_000
    
    @patch('src.hedgefollow.funds.fetch_html')
    def test_scrape_top_funds_fallback(self, mock_fetch):
        """Test fallback avec structure HTML différente."""
        mock_fetch.return_value = MOCK_HTML_DIFFERENT
        
        df = scrape_top_funds()
        
        assert not df.empty
        assert len(df) == 2
        assert df.iloc[0]['name'] == 'Test Fund 1'
    
    @patch('src.hedgefollow.funds.fetch_html')
    def test_scrape_top_funds_no_data(self, mock_fetch):
        """Test avec HTML sans données."""
        mock_fetch.return_value = MOCK_HTML_INVALID
        
        with pytest.raises(ValueError):
            scrape_top_funds()
    
    @patch('src.hedgefollow.funds.fetch_html')
    def test_get_top_n_funds_with_filters(self, mock_fetch):
        """Test sélection avec filtres."""
        mock_fetch.return_value = MOCK_HTML_VALID
        
        # Créer un mock pour éviter la sauvegarde réelle
        with patch('src.hedgefollow.funds.save_df'):
            df = get_top_n_funds(
                n=3,
                min_aum=70_000_000_000,  # 70B minimum
                min_perf_3y=15.0,
                force_refresh=True
            )
        
        assert len(df) <= 3
        assert all(df['aum_usd'] >= 70_000_000_000)
        assert all(df['perf_3y'] >= 15.0)


class TestIntegration:
    """Tests d'intégration end-to-end."""
    
    @pytest.mark.integration
    @patch('src.hedgefollow.funds.fetch_html')
    def test_full_scraping_pipeline(self, mock_fetch):
        """Test du pipeline complet de scraping."""
        mock_fetch.return_value = MOCK_HTML_VALID
        
        # Mock les métriques et alertes
        with patch('src.hedgefollow.funds.track_scraping_quality'):
            with patch('src.hedgefollow.funds.alerts'):
                with patch('src.hedgefollow.funds.save_df'):
                    # Scraper
                    df = scrape_top_funds()
                    
                    # Valider
                    assert DataValidator.validate_funds(df)
                    
                    # Filtrer
                    filtered = get_top_n_funds(
                        n=2,
                        min_aum=100_000_000_000,
                        force_refresh=False  # Utilise le cache du test précédent
                    )
                    
                    assert len(filtered) == 2
                    assert filtered.iloc[0]['name'] == 'Bridgewater Associates'


class TestEdgeCases:
    """Tests des cas limites."""
    
    def test_empty_dataframe_handling(self):
        """Test gestion DataFrame vide."""
        df = pd.DataFrame()
        
        with pytest.raises(ValueError):
            DataValidator.validate_funds(df)
    
    def test_malformed_html(self):
        """Test avec HTML malformé."""
        bad_html = "<table><tr><td>Incomplete"
        soup = make_soup(bad_html)
        
        # Ne doit pas crasher
        assert soup is not None
        assert soup.find("table") is not None
    
    @patch('src.hedgefollow.funds.fetch_html')
    def test_network_error_handling(self, mock_fetch):
        """Test gestion erreur réseau."""
        mock_fetch.side_effect = RuntimeError("Network error")
        
        with pytest.raises(RuntimeError):
            scrape_top_funds()


if __name__ == "__main__":
    # Lancer les tests
    pytest.main([__file__, "-v", "-s"])
