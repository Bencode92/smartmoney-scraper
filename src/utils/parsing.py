"""
Utilitaires pour le parsing HTML et la normalisation des données.
"""
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag
from loguru import logger


def make_soup(html: str) -> BeautifulSoup:
    """
    Crée un objet BeautifulSoup à partir du HTML.
    
    Args:
        html: Contenu HTML brut
        
    Returns:
        Objet BeautifulSoup parsé
    """
    return BeautifulSoup(html, "lxml")


def extract_table_data(table: Tag) -> List[Dict[str, str]]:
    """
    Extrait les données d'un tableau HTML en liste de dictionnaires.
    
    Args:
        table: Element BeautifulSoup <table>
        
    Returns:
        Liste de dictionnaires où chaque dict est une ligne du tableau
    """
    data = []
    
    # Récupérer les headers
    headers = []
    thead = table.find("thead")
    
    if thead:
        # Headers dans thead
        header_row = thead.find("tr")
        if header_row:
            headers = [th.text.strip() for th in header_row.find_all(["th", "td"])]
    else:
        # Headers dans la première ligne
        first_row = table.find("tr")
        if first_row:
            headers = [th.text.strip() for th in first_row.find_all(["th", "td"])]
    
    # Récupérer les données
    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")
    
    # Si pas de thead, ignorer la première ligne (headers)
    if not thead and rows:
        rows = rows[1:]
    
    for row in rows:
        cols = row.find_all(["td", "th"])
        if cols:
            row_data = {}
            for i, col in enumerate(cols):
                if i < len(headers):
                    row_data[headers[i]] = col.text.strip()
                else:
                    row_data[f"col_{i}"] = col.text.strip()
            
            if row_data:  # Ignorer les lignes vides
                data.append(row_data)
    
    logger.debug(f"Extracted {len(data)} rows from table")
    return data


def normalize_ticker(ticker: str) -> str:
    """
    Normalise un symbole boursier.
    
    Args:
        ticker: Symbole brut
        
    Returns:
        Symbole normalisé (uppercase, sans espaces, etc.)
    """
    if not ticker:
        return ""
    
    # Nettoyer et mettre en majuscules
    ticker = ticker.strip().upper()
    
    # Remplacer les tirets par des points pour certains tickers
    # (ex: BRK-B -> BRK.B)
    ticker = ticker.replace("-", ".")
    
    # Enlever les caractères spéciaux sauf le point
    ticker = re.sub(r'[^A-Z0-9.]', '', ticker)
    
    return ticker


def parse_float(value: str) -> Optional[float]:
    """
    Parse une valeur monétaire ou pourcentage en float.
    
    Args:
        value: Chaîne contenant un nombre (peut inclure $, %, M, B, etc.)
        
    Returns:
        Valeur float ou None si impossible à parser
    """
    if not value or value.strip() in ["-", "N/A", "NA", "n/a"]:
        return None
    
    try:
        # Nettoyer la valeur
        value = value.strip()
        
        # Enlever les symboles monétaires et pourcentages
        value = value.replace("$", "").replace(",", "").replace("%", "")
        
        # Gérer les suffixes (M = millions, B = billions, K = milliers)
        multiplier = 1
        if value.endswith("T") or value.endswith("t"):
            multiplier = 1_000_000_000_000
            value = value[:-1]
        elif value.endswith("B") or value.endswith("b"):
            multiplier = 1_000_000_000
            value = value[:-1]
        elif value.endswith("M") or value.endswith("m"):
            multiplier = 1_000_000
            value = value[:-1]
        elif value.endswith("K") or value.endswith("k"):
            multiplier = 1_000
            value = value[:-1]
        
        # Gérer les parenthèses pour les valeurs négatives
        if value.startswith("(") and value.endswith(")"):
            value = "-" + value[1:-1]
        
        return float(value) * multiplier
        
    except (ValueError, AttributeError) as e:
        logger.debug(f"Could not parse float from '{value}': {e}")
        return None


def parse_int(value: str) -> Optional[int]:
    """
    Parse une valeur entière.
    
    Args:
        value: Chaîne contenant un nombre entier
        
    Returns:
        Valeur int ou None si impossible à parser
    """
    parsed = parse_float(value)
    return int(parsed) if parsed is not None else None


def slugify(text: str) -> str:
    """
    Convertit un texte en identifiant slug.
    
    Args:
        text: Texte à convertir
        
    Returns:
        Slug (minuscules, tirets au lieu d'espaces)
    """
    if not text:
        return ""
    
    # Minuscules
    text = text.lower()
    
    # Remplacer les espaces et caractères spéciaux par des tirets
    text = re.sub(r'[^a-z0-9]+', '-', text)
    
    # Enlever les tirets au début et à la fin
    text = text.strip('-')
    
    # Remplacer les tirets multiples par un seul
    text = re.sub(r'-+', '-', text)
    
    return text


def clean_text(text: str) -> str:
    """
    Nettoie un texte en enlevant les espaces superflus.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte nettoyé
    """
    if not text:
        return ""
    
    # Remplacer les espaces multiples par un seul
    text = re.sub(r'\s+', ' ', text)
    
    # Enlever les espaces au début et à la fin
    return text.strip()