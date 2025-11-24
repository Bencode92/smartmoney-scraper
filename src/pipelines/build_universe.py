"""
Pipeline pour construire l'univers consolidé SmartMoney.
Agrège les données de HedgeFollow et Dataroma.
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

from src.config import (
    RAW_HF_DIR,
    RAW_DTR_DIR,
    PROCESSED_DATA_DIR,
    DATE_FORMAT
)
from src.utils.parsing import normalize_ticker
from src.utils.io import (
    load_df,
    save_df,
    get_dated_filename,
    get_latest_file,
    ensure_columns
)


def load_hedgefollow_data() -> Dict[str, pd.DataFrame]:
    """
    Charge toutes les données HedgeFollow disponibles.
    
    Returns:
        Dict avec les DataFrames par type
    """
    logger.info("Loading HedgeFollow data...")
    
    data = {}
    
    # Holdings
    holdings_file = get_latest_file(RAW_HF_DIR, "holdings_*.csv")
    if holdings_file:
        data["hf_holdings"] = load_df(holdings_file)
        logger.info(f"Loaded {len(data['hf_holdings'])} HedgeFollow holdings")
    
    # Insiders
    insiders_file = get_latest_file(RAW_HF_DIR, "insiders_*.csv")
    if insiders_file:
        data["hf_insiders"] = load_df(insiders_file)
        logger.info(f"Loaded {len(data['hf_insiders'])} HedgeFollow insider trades")
    
    # Screener
    screener_file = get_latest_file(RAW_HF_DIR, "screener_*.csv")
    if screener_file:
        data["hf_screener"] = load_df(screener_file)
        logger.info(f"Loaded {len(data['hf_screener'])} HedgeFollow screener results")
    
    return data


def load_dataroma_data() -> Dict[str, pd.DataFrame]:
    """
    Charge toutes les données Dataroma disponibles.
    
    Returns:
        Dict avec les DataFrames par type
    """
    logger.info("Loading Dataroma data...")
    
    data = {}
    
    # Holdings
    holdings_file = get_latest_file(RAW_DTR_DIR, "holdings_*.csv")
    if holdings_file:
        data["dtr_holdings"] = load_df(holdings_file)
        logger.info(f"Loaded {len(data['dtr_holdings'])} Dataroma holdings")
    
    # Grand Portfolio
    grand_file = get_latest_file(RAW_DTR_DIR, "grand_portfolio_*.csv")
    if grand_file:
        data["dtr_grand"] = load_df(grand_file)
        logger.info(f"Loaded {len(data['dtr_grand'])} Grand Portfolio entries")
    
    # Real-time Insiders
    insiders_file = get_latest_file(RAW_DTR_DIR, "realtime_insider_*.csv")
    if insiders_file:
        data["dtr_insiders"] = load_df(insiders_file)
        logger.info(f"Loaded {len(data['dtr_insiders'])} Dataroma insider trades")
    
    return data


def aggregate_by_ticker(
    hf_data: Dict[str, pd.DataFrame],
    dtr_data: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Agrège toutes les données par ticker.
    
    Args:
        hf_data: Données HedgeFollow
        dtr_data: Données Dataroma
        
    Returns:
        DataFrame agrégé par ticker
    """
    logger.info("Aggregating data by ticker...")
    
    # Liste pour stocker les agrégations
    aggregations = []
    
    # --- HedgeFollow Holdings ---
    if "hf_holdings" in hf_data and not hf_data["hf_holdings"].empty:
        df = hf_data["hf_holdings"].copy()
        df["ticker"] = df["ticker"].apply(normalize_ticker)
        
        # Agréger par ticker
        hf_agg = df.groupby("ticker").agg({
            "fund_id": "nunique",  # Nombre de fonds HF
            "weight_in_fund": "mean",  # Poids moyen
            "value_usd": "sum",  # Valeur totale
            "company_name": "first"
        }).reset_index()
        
        hf_agg.rename(columns={
            "fund_id": "num_hf",
            "weight_in_fund": "avg_weight_hf",
            "value_usd": "total_value_hf"
        }, inplace=True)
        
        aggregations.append(hf_agg)
    
    # --- Dataroma Holdings ---
    if "dtr_holdings" in dtr_data and not dtr_data["dtr_holdings"].empty:
        df = dtr_data["dtr_holdings"].copy()
        df["ticker"] = df["ticker"].apply(normalize_ticker)
        
        # Agréger par ticker
        dtr_agg = df.groupby("ticker").agg({
            "manager_id": "nunique",  # Nombre de superinvestors
            "weight_in_portfolio": "mean",  # Poids moyen
            "value_usd": "sum",  # Valeur totale
            "company_name": "first"
        }).reset_index()
        
        dtr_agg.rename(columns={
            "manager_id": "num_si",
            "weight_in_portfolio": "avg_weight_si",
            "value_usd": "total_value_si"
        }, inplace=True)
        
        aggregations.append(dtr_agg)
    
    # --- Grand Portfolio ---
    if "dtr_grand" in dtr_data and not dtr_data["dtr_grand"].empty:
        df = dtr_data["dtr_grand"].copy()
        df["ticker"] = df["ticker"].apply(normalize_ticker)
        
        # Sélectionner les colonnes pertinentes
        grand_agg = df[["ticker", "num_investors", "total_value_usd", "avg_weight"]].copy()
        grand_agg["in_grand_portfolio"] = True
        grand_agg.rename(columns={
            "num_investors": "grand_num_investors",
            "total_value_usd": "grand_total_value",
            "avg_weight": "grand_avg_weight"
        }, inplace=True)
        
        aggregations.append(grand_agg)
    
    # --- HedgeFollow Insiders ---
    if "hf_insiders" in hf_data and not hf_data["hf_insiders"].empty:
        df = hf_data["hf_insiders"].copy()
        df["ticker"] = df["ticker"].apply(normalize_ticker)
        
        # Calculer le net par ticker
        insider_hf = df.groupby(["ticker", "transaction_type"])["transaction_value_usd"].sum().unstack(fill_value=0)
        
        if "Buy" in insider_hf.columns:
            insider_hf["insider_hf_net_buy"] = insider_hf.get("Buy", 0) - insider_hf.get("Sell", 0)
        else:
            insider_hf["insider_hf_net_buy"] = -insider_hf.get("Sell", 0)
        
        insider_hf["insider_hf_num_trades"] = df.groupby("ticker").size()
        insider_hf = insider_hf.reset_index()
        
        aggregations.append(insider_hf[["ticker", "insider_hf_net_buy", "insider_hf_num_trades"]])
    
    # --- Dataroma Insiders ---
    if "dtr_insiders" in dtr_data and not dtr_data["dtr_insiders"].empty:
        df = dtr_data["dtr_insiders"].copy()
        df["ticker"] = df["ticker"].apply(normalize_ticker)
        
        # Calculer le net par ticker
        insider_dtr = df.groupby(["ticker", "transaction_type"])["transaction_value_usd"].sum().unstack(fill_value=0)
        
        if "Buy" in insider_dtr.columns:
            insider_dtr["insider_dtr_net_buy"] = insider_dtr.get("Buy", 0) - insider_dtr.get("Sell", 0)
        else:
            insider_dtr["insider_dtr_net_buy"] = -insider_dtr.get("Sell", 0)
        
        insider_dtr["insider_dtr_num_trades"] = df.groupby("ticker").size()
        insider_dtr = insider_dtr.reset_index()
        
        aggregations.append(insider_dtr[["ticker", "insider_dtr_net_buy", "insider_dtr_num_trades"]])
    
    # --- Merger toutes les agrégations ---
    if not aggregations:
        logger.warning("No data to aggregate")
        return pd.DataFrame()
    
    # Commencer avec la première agrégation
    result = aggregations[0]
    
    # Merger les autres
    for agg_df in aggregations[1:]:
        result = pd.merge(
            result,
            agg_df,
            on="ticker",
            how="outer",
            suffixes=("", "_dup")
        )
        
        # Gérer les colonnes dupliquées (company_name)
        for col in result.columns:
            if col.endswith("_dup"):
                base_col = col[:-4]
                result[base_col] = result[base_col].fillna(result[col])
                result.drop(col, axis=1, inplace=True)
    
    # Remplir les valeurs manquantes
    result = result.fillna({
        "num_hf": 0,
        "num_si": 0,
        "avg_weight_hf": 0,
        "avg_weight_si": 0,
        "total_value_hf": 0,
        "total_value_si": 0,
        "in_grand_portfolio": False,
        "grand_num_investors": 0,
        "grand_total_value": 0,
        "grand_avg_weight": 0,
        "insider_hf_net_buy": 0,
        "insider_hf_num_trades": 0,
        "insider_dtr_net_buy": 0,
        "insider_dtr_num_trades": 0
    })
    
    # Calculer un score de conviction global
    result["smartmoney_score"] = (
        result["num_hf"] * 2 +  # Poids sur le nombre de hedge funds
        result["num_si"] * 3 +  # Poids sur les superinvestors
        (result["in_grand_portfolio"].astype(int) * 5) +  # Bonus Grand Portfolio
        (result["insider_hf_net_buy"] > 0).astype(int) * 2 +  # Bonus achats insiders
        (result["insider_dtr_net_buy"] > 0).astype(int) * 2
    )
    
    # Trier par score
    result = result.sort_values("smartmoney_score", ascending=False)
    
    # Ajouter la date de génération
    result["generated_at"] = datetime.now().isoformat()
    
    logger.info(f"Aggregated data for {len(result)} unique tickers")
    
    return result


def build_universe() -> pd.DataFrame:
    """
    Construit l'univers SmartMoney complet.
    
    Returns:
        DataFrame de l'univers consolidé
    """
    logger.info("Building SmartMoney universe...")
    
    # Charger les données
    hf_data = load_hedgefollow_data()
    dtr_data = load_dataroma_data()
    
    # Vérifier qu'on a des données
    if not hf_data and not dtr_data:
        logger.error("No data available to build universe")
        return pd.DataFrame()
    
    # Agréger par ticker
    universe = aggregate_by_ticker(hf_data, dtr_data)
    
    if universe.empty:
        logger.error("Failed to build universe")
        return universe
    
    # Filtrer les tickers vides ou invalides
    universe = universe[universe["ticker"].str.len() > 0]
    universe = universe[~universe["ticker"].str.contains(r'^\d+$', na=False)]  # Exclure les tickers purement numériques
    
    # Stats finales
    logger.info(f"Universe built with {len(universe)} tickers")
    logger.info(f"Top conviction stocks (score > 10): {len(universe[universe['smartmoney_score'] > 10])}")
    logger.info(f"Stocks in Grand Portfolio: {universe['in_grand_portfolio'].sum()}")
    logger.info(f"Stocks with insider buying: {(universe['insider_hf_net_buy'] > 0).sum() + (universe['insider_dtr_net_buy'] > 0).sum()}")
    
    return universe


def save_universe(universe: pd.DataFrame) -> Path:
    """
    Sauvegarde l'univers avec horodatage.
    
    Args:
        universe: DataFrame de l'univers
        
    Returns:
        Path du fichier sauvé
    """
    filename = get_dated_filename("universe_smartmoney")
    output_path = PROCESSED_DATA_DIR / filename
    
    save_df(universe, output_path)
    logger.info(f"Universe saved to {output_path}")
    
    return output_path


if __name__ == "__main__":
    # Exécution directe : construire et sauvegarder l'univers
    universe = build_universe()
    
    if not universe.empty:
        output_path = save_universe(universe)
        
        # Afficher un résumé
        print(f"\n=== SmartMoney Universe Built ===")
        print(f"Total tickers: {len(universe)}")
        print(f"Output: {output_path}")
        
        # Top 20 par score
        print("\n=== Top 20 by SmartMoney Score ===")
        top20 = universe.head(20)[
            ["ticker", "company_name", "smartmoney_score", 
             "num_hf", "num_si", "in_grand_portfolio",
             "insider_hf_net_buy", "insider_dtr_net_buy"]
        ]
        print(top20.to_string())
        
        # Stats par catégorie
        print("\n=== Category Statistics ===")
        print(f"Held by hedge funds only: {len(universe[(universe['num_hf'] > 0) & (universe['num_si'] == 0)])}")
        print(f"Held by superinvestors only: {len(universe[(universe['num_si'] > 0) & (universe['num_hf'] == 0)])}")
        print(f"Held by both: {len(universe[(universe['num_hf'] > 0) & (universe['num_si'] > 0)])}")
        print(f"With insider buying activity: {len(universe[(universe['insider_hf_net_buy'] > 0) | (universe['insider_dtr_net_buy'] > 0)])}")
    else:
        print("Failed to build universe - no data available")