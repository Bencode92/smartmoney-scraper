"""
Utilitaires pour le parsing HTML et la normalisation des données.
"""
import re
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup, Tag
from loguru import logger


def make_soup(html: str) -> BeautifulSoup:
    """Crée un objet BeautifulSoup à partir du HTML."""
    return BeautifulSoup(html, "lxml")


def extract_table_data(table: Tag) -> List[Dict[str, str]]:
    """Extrait les données d'un tableau HTML en liste de dictionnaires."""
    data: List[Dict[str, str]] = []

    headers: List[str] = []
    thead = table.find("thead")
    if thead:
        header_row = thead.find("tr")
        if header_row:
            headers = [th.text.strip() for th in header_row.find_all(["th", "td"])]
    else:
        first_row = table.find("tr")
        if first_row:
            headers = [th.text.strip() for th in first_row.find_all(["th", "td"])]

    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    if not thead and rows:
        rows = rows[1:]

    for row in rows:
        cols = row.find_all(["td", "th"])
        if not cols:
            continue
        row_data: Dict[str, str] = {}
        for i, col in enumerate(cols):
            if i < len(headers):
                row_data[headers[i]] = col.text.strip()
            else:
                row_data[f"col_{i}"] = col.text.strip()
        if row_data:
            data.append(row_data)

    logger.debug(f"Extracted {len(data)} rows from table")
    return data


def normalize_ticker(ticker: str) -> str:
    """Normalise un symbole boursier."""
    if not ticker:
        return ""
    ticker = ticker.strip().upper()
    ticker = ticker.replace("-", ".")
    ticker = re.sub(r"[^A-Z0-9.]", "", ticker)
    return ticker


def parse_float(value: str) -> Optional[float]:
    """Parse une valeur monétaire ou pourcentage en float."""
    if not value or value.strip() in ["-", "N/A", "NA", "n/a"]:
        return None
    try:
        cleaned = value.strip().replace("$", "").replace(",", "").replace("%", "")
        multiplier = 1
        if cleaned.endswith(("T", "t")):
            multiplier = 1_000_000_000_000
            cleaned = cleaned[:-1]
        elif cleaned.endswith(("B", "b")):
            multiplier = 1_000_000_000
            cleaned = cleaned[:-1]
        elif cleaned.endswith(("M", "m")):
            multiplier = 1_000_000
            cleaned = cleaned[:-1]
        elif cleaned.endswith(("K", "k")):
            multiplier = 1_000
            cleaned = cleaned[:-1]
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        return float(cleaned) * multiplier
    except (ValueError, AttributeError) as e:
        logger.debug(f"Could not parse float from '{value}': {e}")
        return None


def parse_int(value: str) -> Optional[int]:
    """Parse une valeur entière."""
    parsed = parse_float(value)
    return int(parsed) if parsed is not None else None


def slugify(text: str) -> str:
    """Convertit un texte en identifiant slug."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    text = re.sub(r"-+", "-", text)
    return text


def clean_text(text: str) -> str:
    """Nettoie un texte en enlevant les espaces superflus."""
    if not text:
        return ""
    collapsed = re.sub(r"\s+", " ", text)
    return collapsed.strip()
