"""
Utilitaires pour la lecture/écriture des données (CSV, SQLite).
"""
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
from loguru import logger

from src.config import DATE_FORMAT


def save_df(df: pd.DataFrame, path: Path, index: bool = False, mode: str = "w") -> None:
    """Sauvegarde un DataFrame en CSV."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=index, mode=mode, header=(mode == "w"))
        logger.info(f"Saved {len(df)} rows to {path}")
    except Exception as e:
        logger.error(f"Failed to save DataFrame to {path}: {e}")
        raise


def append_df(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    """Ajoute un DataFrame à un CSV existant."""
    mode = "a" if path.exists() else "w"
    save_df(df, path, index=index, mode=mode)


def load_df(path: Path) -> Optional[pd.DataFrame]:
    """Charge un DataFrame depuis un CSV."""
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return None
    try:
        df = pd.read_csv(path)
        logger.info(f"Loaded {len(df)} rows from {path}")
        return df
    except Exception as e:
        logger.error(f"Failed to load DataFrame from {path}: {e}")
        return None


def get_dated_filename(base_name: str, extension: str = "csv") -> str:
    """Génère un nom de fichier avec la date du jour."""
    date_str = datetime.now().strftime(DATE_FORMAT)
    return f"{base_name}_{date_str}.{extension}"


def get_latest_file(directory: Path, pattern: str) -> Optional[Path]:
    """Trouve le fichier le plus récent correspondant au pattern."""
    files = list(directory.glob(pattern))
    if not files:
        logger.debug(f"No files matching {pattern} in {directory}")
        return None
    latest = max(files, key=lambda f: f.stat().st_mtime)
    logger.debug(f"Found latest file: {latest}")
    return latest


def merge_dataframes(*dfs: pd.DataFrame) -> pd.DataFrame:
    """Fusionne plusieurs DataFrames verticalement."""
    valid_dfs = [df for df in dfs if df is not None and not df.empty]
    if not valid_dfs:
        logger.warning("No valid DataFrames to merge")
        return pd.DataFrame()
    merged = pd.concat(valid_dfs, ignore_index=True)
    logger.info(f"Merged {len(valid_dfs)} DataFrames into {len(merged)} rows")
    return merged


def ensure_columns(df: pd.DataFrame, columns: Dict[str, Any]) -> pd.DataFrame:
    """S'assure qu'un DataFrame contient certaines colonnes avec des valeurs par défaut."""
    for col, default_value in columns.items():
        if col not in df.columns:
            df[col] = default_value
    return df
