"""
Validateurs pour assurer la qualité et cohérence des données scrapées.
"""
from typing import List, Optional
import pandas as pd
from loguru import logger


class DataValidator:
    """Validateur pour les données de hedge funds et holdings."""
    
    MIN_FUNDS = 5
    MIN_HOLDINGS = 10
    REQUIRED_FUND_COLUMNS = ['fund_id', 'name', 'aum_usd']
    REQUIRED_HOLDING_COLUMNS = ['ticker', 'name', 'value', 'shares']
    
    @staticmethod
    def validate_funds(df: pd.DataFrame, min_funds: int = None) -> bool:
        """
        Valide les données des fonds.
        
        Args:
            df: DataFrame des fonds
            min_funds: Nombre minimum de fonds attendu
            
        Returns:
            True si valide
            
        Raises:
            ValueError: Si validation échoue
        """
        min_funds = min_funds or DataValidator.MIN_FUNDS
        
        # Vérifier qu'on a assez de données
        if len(df) < min_funds:
            raise ValueError(
                f"Seulement {len(df)} fonds trouvés, minimum attendu: {min_funds}. "
                "Structure HTML probablement changée."
            )
        
        # Vérifier les colonnes requises
        missing = set(DataValidator.REQUIRED_FUND_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes dans funds data: {missing}")
        
        # Vérifier qu'on a au moins 50% des AUM
        aum_coverage = df['aum_usd'].notna().sum() / len(df)
        if aum_coverage < 0.5:
            logger.warning(f"Seulement {aum_coverage:.1%} des AUM disponibles")
        
        # Vérifier les fund_id uniques
        if df['fund_id'].duplicated().any():
            duplicates = df[df['fund_id'].duplicated()]['fund_id'].tolist()
            raise ValueError(f"Fund IDs dupliqués: {duplicates}")
        
        # Vérifier les valeurs aberrantes
        if 'aum_usd' in df.columns:
            valid_aum = df['aum_usd'].dropna()
            if len(valid_aum) > 0:
                if (valid_aum < 0).any():
                    raise ValueError("AUM négatifs détectés")
                if (valid_aum > 1e14).any():  # > 100 trillions
                    logger.warning("AUM suspicieusement élevés détectés")
        
        logger.info(f"✅ Validation réussie: {len(df)} fonds valides")
        return True
    
    @staticmethod
    def validate_holdings(df: pd.DataFrame, min_holdings: int = None) -> bool:
        """
        Valide les données des holdings.
        
        Args:
            df: DataFrame des holdings
            min_holdings: Nombre minimum de positions attendu
            
        Returns:
            True si valide
            
        Raises:
            ValueError: Si validation échoue
        """
        min_holdings = min_holdings or DataValidator.MIN_HOLDINGS
        
        if len(df) < min_holdings:
            raise ValueError(
                f"Seulement {len(df)} holdings trouvés, minimum attendu: {min_holdings}"
            )
        
        # Vérifier les colonnes requises
        missing = set(DataValidator.REQUIRED_HOLDING_COLUMNS) - set(df.columns)
        if missing:
            logger.warning(f"Colonnes manquantes dans holdings: {missing}")
        
        # Vérifier les tickers
        if 'ticker' in df.columns:
            invalid_tickers = df[df['ticker'].str.len() > 10]['ticker'].unique()
            if len(invalid_tickers) > 0:
                logger.warning(f"Tickers suspects (>10 chars): {invalid_tickers[:5]}")
        
        # Vérifier les valeurs
        if 'value' in df.columns:
            if (df['value'] < 0).any():
                raise ValueError("Valeurs négatives dans holdings")
        
        logger.info(f"✅ Validation réussie: {len(df)} holdings valides")
        return True
    
    @staticmethod
    def validate_insiders(df: pd.DataFrame) -> bool:
        """
        Valide les données d'insider trading.
        
        Args:
            df: DataFrame des trades insiders
            
        Returns:
            True si valide
        """
        if df.empty:
            logger.warning("Aucun trade insider trouvé")
            return True
        
        required = ['ticker', 'insider_name', 'transaction_type', 'value']
        missing = set(required) - set(df.columns)
        if missing:
            logger.warning(f"Colonnes manquantes dans insiders: {missing}")
        
        # Vérifier les types de transactions
        if 'transaction_type' in df.columns:
            valid_types = ['Buy', 'Sell', 'Option Exercise', 'Gift']
            invalid = df[~df['transaction_type'].isin(valid_types)]
            if len(invalid) > 0:
                logger.warning(f"Types de transaction non reconnus: {invalid['transaction_type'].unique()}")
        
        return True
    
    @staticmethod
    def check_data_freshness(df: pd.DataFrame, date_col: str = 'scraped_at', max_days: int = 7) -> bool:
        """
        Vérifie que les données ne sont pas trop vieilles.
        
        Args:
            df: DataFrame avec colonne de date
            date_col: Nom de la colonne de date
            max_days: Age maximum en jours
            
        Returns:
            True si les données sont fraîches
        """
        if date_col not in df.columns:
            logger.warning(f"Colonne {date_col} non trouvée, impossible de vérifier la fraîcheur")
            return True
        
        try:
            df[date_col] = pd.to_datetime(df[date_col])
            oldest = df[date_col].min()
            age_days = (pd.Timestamp.now() - oldest).days
            
            if age_days > max_days:
                logger.warning(f"Données vieilles de {age_days} jours (max: {max_days})")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de fraîcheur: {e}")
            return True


class ScrapingValidator:
    """Validateur pour les résultats de scraping HTML."""
    
    @staticmethod
    def validate_html_structure(soup, expected_elements: dict) -> bool:
        """
        Vérifie que la structure HTML contient les éléments attendus.
        
        Args:
            soup: BeautifulSoup object
            expected_elements: Dict des sélecteurs CSS et descriptions
            
        Returns:
            True si tous les éléments sont trouvés
            
        Raises:
            ValueError: Si des éléments manquent
        """
        missing = []
        
        for selector, description in expected_elements.items():
            element = soup.select_one(selector)
            if not element:
                missing.append(f"{description} (selector: {selector})")
        
        if missing:
            raise ValueError(
                f"Structure HTML changée! Éléments manquants: {', '.join(missing)}. "
                "Le site a peut-être été mis à jour."
            )
        
        return True
    
    @staticmethod
    def validate_table_headers(table, expected_headers: List[str], fuzzy: bool = True) -> bool:
        """
        Vérifie que les headers d'un tableau correspondent.
        
        Args:
            table: Element table BeautifulSoup
            expected_headers: Headers attendus
            fuzzy: Si True, fait une comparaison approximative
            
        Returns:
            True si les headers correspondent
        """
        headers = [th.text.strip().lower() for th in table.find_all('th')]
        
        if not headers:
            raise ValueError("Aucun header trouvé dans le tableau")
        
        if fuzzy:
            # Vérification approximative
            for expected in expected_headers:
                if not any(expected.lower() in h for h in headers):
                    logger.warning(f"Header attendu '{expected}' non trouvé dans {headers}")
        else:
            # Vérification exacte
            headers_set = set(headers)
            expected_set = set(h.lower() for h in expected_headers)
            missing = expected_set - headers_set
            if missing:
                raise ValueError(f"Headers manquants: {missing}")
        
        return True


def validate_scraping_result(df: pd.DataFrame, data_type: str = 'funds') -> pd.DataFrame:
    """
    Fonction helper pour valider un résultat de scraping.
    
    Args:
        df: DataFrame à valider
        data_type: Type de données ('funds', 'holdings', 'insiders')
        
    Returns:
        DataFrame validé
        
    Raises:
        ValueError: Si validation échoue
    """
    if df.empty:
        raise ValueError(f"DataFrame vide pour {data_type}")
    
    validator = DataValidator()
    
    if data_type == 'funds':
        validator.validate_funds(df)
    elif data_type == 'holdings':
        validator.validate_holdings(df)
    elif data_type == 'insiders':
        validator.validate_insiders(df)
    else:
        logger.warning(f"Type de données non reconnu: {data_type}")
    
    # Vérifier la fraîcheur si applicable
    if 'scraped_at' in df.columns:
        validator.check_data_freshness(df)
    
    return df
